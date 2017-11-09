import json
import time
from json import JSONDecodeError
from queue import Queue
from threading import Lock, Thread

import requests
import urllib3
from sseclient import SSEClient

from alto.unicorn.definitions import Definitions
from alto.unicorn.exceptions import UnknownEventType
from alto.unicorn.logger import logger
from alto.unicorn.models.domains import DomainDataProvider
from alto.unicorn.models.flows import FlowDataProvider, Flow
from alto.unicorn.models.queries import QueryDataProvider, QueryItem, DomainQuery
from alto.unicorn.models.singleton import SingletonType


class UpdateStreamThread(Thread):
    def __init__(self, domain_name, update_url):
        super(UpdateStreamThread, self).__init__()
        self.domain_name = domain_name  # type: str
        self.update_url = update_url  # type: str
        ThreadDataProvider().add_update_thread(domain_name, self)

    def get_sseclient(self):
        """Get SSEClient from url"""
        http = urllib3.PoolManager()
        response = http.request("GET", self.update_url, preload_content=False)
        return SSEClient(response)

    def handle_update_event(self, update_event, callback=None):
        """Handle update event received from server"""
        query_id = update_event["query-id"]
        response = update_event["response"]
        query_obj = QueryDataProvider().get(query_id)
        query_obj.get_domain_query(self.domain_name).response = response
        if callback:
            callback(query_obj)

    def start_control_stream_thread(self, control_url):
        logger.info("Start control stream: " + control_url)
        thread = ControlStreamThread(self.domain_name, control_url)
        thread.start()

    def run(self):
        """ Start the update stream thread """

        # Wait some time to let server up
        time.sleep(Definitions.WAIT_TIME_AFTER_REG)

        # Send a request to remote
        client = self.get_sseclient()

        # handle every received event
        for event in client.events():
            if event.event == Definitions.EventType.UPDATE_STREAM:
                control_stream_url = event.data
                ThreadDataProvider().add_control_thread(self.domain_name,
                                                        self.start_control_stream_thread(control_stream_url))
                DomainDataProvider()[self.domain_name].control_url = control_stream_url
            elif event.event == Definitions.EventType.JSON:
                update_event = json.loads(event.data)
                update_thread = Thread(target=self.handle_update_event, args=[update_event, self.update_queries])
                update_thread.start()
            else:
                raise UnknownEventType(event)

    def update_queries(self, query_obj):
        """
        :type query_obj: Query
        """
        if query_obj.query_type == "path-query":
            self.update_path_query(query_obj.get_domain_query(self.domain_name))
        elif query_obj.query_type == "resource-query":
            self.update_resource_query(query_obj.get_domain_query(self.domain_name))

    def update_path_query(self, domain_query):
        """
        :type domain_query: DomainQuery
        """
        query_items = domain_query.query_items
        response = domain_query.response
        path_data = list(zip(query_items, response))
        next_flow_ids = list()
        for query_item, next_hop in path_data:
            flow_obj = FlowDataProvider().get(query_item.flow_id)
            if flow_obj.has_domain(self.domain_name):
                flow_obj.delete_path_after_hop(self.domain_name)
            flow_obj.add_hop(next_hop)

            # Judge if the flow has reached the destination
            if flow_obj.last_hop != "" and DomainDataProvider().has_ip(
                    flow_obj.last_hop) and DomainDataProvider().get_domain(
                flow_obj.last_hop).domain_name == DomainDataProvider().get_domain(flow_obj.dst_ip).domain_name:
                flow_obj.complete()
            else:
                next_flow_ids.append(flow_obj.flow_id)
        ThreadDataProvider().get_task_handler_thread(domain_query.query_id).path_query(next_flow_ids)

    def update_resource_query(self, domain_query):
        """
        :type domain_query: DomainQuery
        :return:
        """
        logger.debug("update resource query: " + domain_query.domain_name)
        ThreadDataProvider().get_task_handler_thread(domain_query.query_id).add_resource_query_response(
            domain_query.domain_name, domain_query.response)


class ControlStreamThread(Thread):
    def __init__(self, domain_name, control_url):
        super(ControlStreamThread, self).__init__()
        self.domain_name = domain_name
        self.control_url = control_url
        ThreadDataProvider().add_control_thread(domain_name, self)
        self.new_requests = Queue()
        self._new_requests_lock = Lock()

    def get_request(self):
        with self._new_requests_lock:
            request = self.new_requests.get()
        return request

    def add_request(self, request, callback, *args):
        with self._new_requests_lock:
            self.new_requests.put((request, callback, args))

    def handle_request(self, request, callback, args):

        logger.info("POST request to " + self.control_url)

        # Send to remote & get response
        response = requests.post(self.control_url, json=request, headers={'Content-type': 'application/json'})
        try:
            resp = json.loads(response.text)
        except JSONDecodeError as e:
            logger.error("Response is not in json format, use origin response" + response.text)
            resp = response.text

        if callback:
            callback(request, resp, *args)

    def run(self):
        """Start the control stream thread"""

        while True:
            something_to_do = False
            while not self.new_requests.empty():
                something_to_do = True
                (request, callback, args) = self.get_request()
                self.handle_request(request, callback, args)
            if something_to_do:
                pass
            time.sleep(Definitions.POLL_TIME)


class TasksHandlerThread(Thread):
    def __init__(self, tasks):
        super(TasksHandlerThread, self).__init__()

        # Tasks
        self.tasks = tasks

        # Flow ids
        self._flow_ids = list()

        # Query Id
        self._path_query_id = QueryDataProvider().gen_query_id()
        self._resource_query_id = QueryDataProvider().gen_query_id()
        ThreadDataProvider().add_task_handler_thread(self._path_query_id, self)
        ThreadDataProvider().add_task_handler_thread(self._resource_query_id, self)

        # Query Obj
        self._path_query_obj = None
        self._resource_query_obj = None

        # Resource Query
        self.complete_resource_query_number = 0
        self.all_resource_query_number = 0
        self._resource_query_response = dict()  # type: dict[str, str]

        # Is Query Latest
        self._path_query_latest = False
        self._resource_query_latest = False
        self._resource_query_complete = False

        # Lock
        self._path_query_lock = Lock()
        self._resource_query_lock = Lock()

    def run(self):

        # Generate query ids and send them to servers
        self.prepare(self._path_query_id, self._resource_query_id)

        self._path_query_obj = QueryDataProvider().get(self._path_query_id)
        self._resource_query_obj = QueryDataProvider().get(self._resource_query_id)

        self._path_query_obj.query_type = Definitions.QueryType.PATH_QUERY_TYPE
        self._resource_query_obj.query_type = Definitions.QueryType.RESOURCE_QUERY_TYPE

        # Get all flows of the set of tasks
        self._flow_ids = self.get_flows(self.tasks)

        # Get all unrecorded flow_ids, and set their path query id to self._path_query_id
        unrecorded_flow_ids = FlowDataProvider().get_flows_without_path_query_id(self._flow_ids,
                                                                                 self._path_query_id)

        logger.debug("Get " + str(len(self._flow_ids)) + " from given tasks, and " + str(
            len(unrecorded_flow_ids)) + " of them are unrecorded")

        # Do path query
        self.path_query(unrecorded_flow_ids)

        while True:
            complete_flow_ids = set()
            flow_ids = set(self._flow_ids)
            for flow_id in flow_ids:
                flow = FlowDataProvider().get(flow_id)
                if flow.is_complete:
                    complete_flow_ids.add(flow_id)
            if len(complete_flow_ids) >= len(flow_ids):
                self._path_query_latest = True

            if self._path_query_latest and not self._resource_query_complete:
                self.resource_query()

            if self._path_query_latest and self._resource_query_complete and not self._resource_query_latest:
                self.resource_query_complete_operation()

            time.sleep(Definitions.POLL_TIME)

    @staticmethod
    def prepare(path_query_id, resource_query_id):
        """
        Create new path query id and resource query id, then send them to servers
        """
        request_builder = RequestBuilder(
            action=Definitions.QueryAction.NEW,
            query_type=Definitions.QueryType.PATH_QUERY_TYPE,
            query_id=path_query_id
        )
        path_request = request_builder.build()

        request_builder = RequestBuilder(
            action=Definitions.QueryAction.NEW,
            query_type=Definitions.QueryType.RESOURCE_QUERY_TYPE,
            query_id=resource_query_id
        )
        resource_request = request_builder.build()

        logger.debug("Generate path query id " + str(path_query_id))
        logger.debug("Generate resource query id " + str(resource_query_id))

        for domain_name in DomainDataProvider():
            logger.debug("New query id to domain: " + domain_name)
            control_thread = ThreadDataProvider().get_control_thread(domain_name)
            control_thread.add_request(path_request, callback=lambda req, res: logger.debug(
                "Send path query id: " + str(path_query_id) +
                " to domain agent, and get response " + json.dumps(res)))
            control_thread.add_request(resource_request, callback=lambda req, res: logger.debug(
                "Send resource query id: " + str(resource_query_id) +
                " to domain agent, and get response " + json.dumps(res)))

    def path_query(self, query_flow_ids):
        # Group by domain name
        flow_ids_by_domain_name = self.group_by_domain_name(query_flow_ids)
        for domain_name in flow_ids_by_domain_name.keys():
            flow_ids = flow_ids_by_domain_name[domain_name]
            request_builder = RequestBuilder(
                Definitions.QueryAction.ADD,
                Definitions.QueryType.PATH_QUERY_TYPE,
                self._path_query_id
            )
            domain_query = QueryDataProvider().get(self._path_query_id).get_domain_query(domain_name)
            for flow_id in flow_ids:
                flow = FlowDataProvider().get(flow_id)

                # Add the flow to the request
                request_builder.add_item(flow, flow.last_hop)

                # Add the flow to query data store
                domain_query.add_query_item(QueryItem(flow_id, flow.last_hop))

            # Add all domain related info to query data store
            self._path_query_obj.add(domain_query)

            # Build the request and then send it to server
            request_dict = request_builder.build()
            ThreadDataProvider().get_control_thread(domain_name).add_request(request_dict, callback=None)

    def resource_query(self):
        with self._resource_query_lock:
            self.complete_resource_query_number = 0
            domain_flow_ids = self.resource_query_group(self._flow_ids)
            self.all_resource_query_number = len(domain_flow_ids.keys())

            for domain in domain_flow_ids.keys():
                control_thread = ThreadDataProvider().get_control_thread(domain)  # type: ControlStreamThread
                request_builder = RequestBuilder(
                    Definitions.QueryAction.ADD,
                    Definitions.QueryType.RESOURCE_QUERY_TYPE,
                    self._resource_query_id
                )
                for flow_id in domain_flow_ids[domain]:
                    flow = FlowDataProvider().get(flow_id)
                    request_builder.add_item(flow,
                                             QueryDataProvider().get(flow.path_query_id).get_domain_query(
                                                 domain).get_query_item(flow_id).ingress_point
                                             )
                request = request_builder.build()
                control_thread.add_request(request, lambda req, res: logger.debug(
                    "Resource query to " + domain + " get response:" + res.__str__()))

        while self.complete_resource_query_number < self.all_resource_query_number:
            time.sleep(Definitions.POLL_TIME)

        with self._resource_query_lock:
            self._resource_query_complete = True

        self.resource_query_complete_operation()

    def resource_query_complete_operation(self):
        logger.info("Resource query complete")
        with self._resource_query_lock:
            for domain_name in self._resource_query_response:
                response = self._resource_query_response[domain_name]
                print(response)

            self._resource_query_latest = True

    def add_resource_query_response(self, domain_name, response):
        with self._resource_query_lock:
            if domain_name not in self._resource_query_response.keys():
                self.complete_resource_query_number += 1
            self._resource_query_response[domain_name] = response
            self._resource_query_latest = False

    @staticmethod
    def group_by_domain_name(flow_ids):
        group = dict()  # type: dict[str, list[int]]
        for flow_id in flow_ids:
            flow = FlowDataProvider().get(flow_id)
            last_hop = flow.last_hop
            ip = last_hop if last_hop != "" else flow.src_ip  # Source IP / Last hop ip
            domain_name = DomainDataProvider().get_domain(ip).domain_name
            if domain_name not in group:
                group[domain_name] = list()
            group[domain_name].append(flow_id)
        return group

    @staticmethod
    def resource_query_group(flow_ids):
        grouped_flow_ids = dict()
        for flow_id in flow_ids:
            through_domains = FlowDataProvider().get(flow_id).through_domains
            for domain_name in through_domains:
                if domain_name not in grouped_flow_ids:
                    grouped_flow_ids[domain_name] = set()
                grouped_flow_ids[domain_name].add(flow_id)
        return grouped_flow_ids

    @staticmethod
    def get_flows(tasks):
        flow_ids = set()
        for task in tasks:
            jobs = task["jobs"]
            flows_of_jobs = [(
                i["ip"],
                i["port"],
                j["ip"],
                j["port"],
                job["protocol"]
            ) for job in jobs for i in job["potential_srcs"] for j in job["potential_dsts"]]
            flows_of_jobs = set(flows_of_jobs)
            flow_ids = flow_ids.union(set([
                FlowDataProvider().get_flow_id(i) for i in flows_of_jobs
            ]))
        return list(flow_ids)


class RequestBuilder(object):
    def __init__(self, action, query_type, query_id=None):
        self.action = action
        self.query_type = query_type
        if query_id is not None:
            self.query_id = str(query_id)
        self.items = []

    def add_item(self, flow, ingress_point=None):
        """
        :param flow:
        :type flow: Flow
        :param ingress_point:
        :return:
        """
        item = {
            "flow": {
                "flow-id": flow.flow_id,
                "src-ip": flow.src_ip,
                # "src-port": flow.src_port,
                "dst-ip": flow.dst_ip,
                "dst-port": flow.dst_port,
                "protocol": flow.protocol
            }
        }
        if ingress_point:
            item["ingress-point"] = ingress_point
        self.items.append(item)

    def build(self):
        result = {
            "action": self.action,
            "query-type": self.query_type,
            "query-desc": self.items
        }
        if self.query_id:
            result["query-id"] = self.query_id
        return result


def parse_request(request):
    flows = []
    for item in request["query-desc"]:
        flows.append((
            item["flow"]["src-ip"],
            item["flow"]["src-port"],
            item["flow"]["dst-ip"],
            item["flow"]["dst-port"],
            item["flow"]["protocol"]
        ))
    return flows


class ThreadDataProvider(metaclass=SingletonType):
    def __init__(self):
        self._update_stream_threads = dict()  # type: dict[str, UpdateStreamThread]
        self._control_stream_threads = dict()  # type: dict[str, ControlStreamThread]
        self._task_handler_threads = dict()  # type: dict[int, TasksHandlerThread]
        self._lock = Lock()

    def has_update_thread(self, domain_name):
        return domain_name in self._update_stream_threads

    def has_control_thread(self, domain_name):
        return domain_name in self._control_stream_threads

    def has_task_handler_thread(self, query_id):
        return query_id in self._task_handler_threads

    def get_update_thread(self, domain_name):
        return self._update_stream_threads[domain_name]

    def get_control_thread(self, domain_name):
        return self._control_stream_threads[domain_name]

    def get_task_handler_thread(self, query_id):
        return self._task_handler_threads[query_id]

    def add_update_thread(self, domain_name, thread):
        if thread is not None:
            self.remove_update_thread(domain_name)
            with self._lock:
                self._update_stream_threads[domain_name] = thread

    def add_control_thread(self, domain_name, thread):
        if thread is not None:
            self.remove_control_thread(domain_name)
            with self._lock:
                self._control_stream_threads[domain_name] = thread

    def add_task_handler_thread(self, query_id, thread):
        self.remove_task_handler_thread(query_id)
        with self._lock:
            self._task_handler_threads[query_id] = thread

    def remove_update_thread(self, domain_name):
        if self.has_update_thread(domain_name):
            with self._lock:
                del self._update_stream_threads[domain_name]

    def remove_control_thread(self, domain_name):
        if self.has_control_thread(domain_name):
            with self._lock:
                del self._control_stream_threads[domain_name]

    def remove_task_handler_thread(self, query_id):
        if self.has_task_handler_thread(query_id):
            with self._lock:
                del self._task_handler_threads[query_id]