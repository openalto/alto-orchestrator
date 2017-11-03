import json
import time
from queue import Queue
from threading import Thread, Lock

import urllib3
from sseclient import SSEClient

from alto.unicorn.data_provider import QueryData, DomainData, ThreadData, FlowData, Hop
from alto.unicorn.definitions import Definitions
from alto.unicorn.exceptions import UnknownEventType, UnknownIP


class UpdateStreamThread(Thread):
    def __init__(self, domain_name, update_url):
        super(UpdateStreamThread, self).__init__()
        self.domain_name = domain_name
        self.update_url = update_url
        ThreadData().add_update_thread(domain_name, self)

    def get_sseclient(self):
        """Get SSEClient from url"""
        http = urllib3.PoolManager()
        response = http.request("GET", self.update_url, preload_content=False)
        return SSEClient(response)

    def start_control_stream_thread(self, control_url):
        """Start control stream"""
        control_stream_thread = ControlStreamThread(self.domain_name, control_url)
        control_stream_thread.start()

    def handle_update_event(self, update_event, callback):
        """Handle update event received from server"""
        query_id = update_event["query-id"]
        response = update_event["response"]
        query_obj = QueryData().get(query_id=query_id)
        query_obj.result = response
        callback(query_obj)

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
                DomainData()[self.domain_name].control_url = control_stream_url
            elif event.event == Definitions.EventType.JSON:
                update_event = json.loads(event.data)
                update_thread = Thread(target=self.handle_update_event, args=[update_event, self.update_queries])
                update_thread.start()
            else:
                raise UnknownEventType(event)

    def update_queries(self, query_obj):
        """
        :type query_obj: QueryData.Query
        """
        flows = parse_request(query_obj.request)
        response = query_obj.result
        path_data = list(zip(flows, response))
        for flow, next_hop in path_data:
            flow_obj = FlowData().get(flow)
            if flow_obj.has_domain(self.domain_name):
                flow_obj.delete_path_after_hop(self.domain_name)
            hop = Hop()
            hop.domain_name = self.domain_name
            hop.ip = next_hop
            flow_obj.path.append(hop)


class ControlStreamThread(Thread):
    def __init__(self, domain_name, control_url):
        super(ControlStreamThread, self).__init__()
        self.domain_name = domain_name
        self.control_url = control_url
        ThreadData().add_control_thread(domain_name, self)
        self.new_requests = Queue()
        self.new_requests_lock = Lock()

    def get_request(self):
        self.new_requests_lock.acquire()
        request = self.new_requests.get()
        self.new_requests_lock.release()
        return request

    def add_request(self, request, callback, *args):
        self.new_requests_lock.acquire()
        self.new_requests.put((request, callback, args))
        self.new_requests_lock.release()

    def handle_request(self, request, callback, args):

        # Send to remote & get response
        response = requests.post(self.control_url, data=request)
        resp = json.loads(response.text)

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
        self.flow_ids = list()
        self.tasks = tasks
        self.path_query_complete_flow_ids = set()
        self._path_query_id = QueryData().gen_query_id()
        self._resource_query_id = QueryData().gen_query_id()

    def prepare(self):
        for domain_name in DomainData():
            control_thread = ThreadData().get_control_thread(domain_name)
            request_builder = RequestBuilder(
                action=Definitions.QueryAction.NEW,
                query_type=Definitions.QueryType.PATH_QUERY_TYPE,
                query_id=self._path_query_id
            )
            request = request_builder.build()
            control_thread.add_request(request)

            request_builder = RequestBuilder(
                action=Definitions.QueryAction.NEW,
                query_type=Definitions.QueryType.RESOURCE_QUERY_TYPE,
                query_id=self._resource_query_id
            )
            request = request_builder.build()
            control_thread.add_request(request)

    @staticmethod
    def group_by_domain_name(flow_ids):
        group = dict()
        for flow_id in flow_ids:
            flow = FlowData().get(flow_id)
            last_hop = flow.last_hop
            ip = last_hop if last_hop != "" else flow.src_ip  # Source IP / Last hop ip
            domain_name = DomainData().get_domain(ip).domain_name
            if domain_name not in group:
                group[domain_name] = list()
            group[domain_name].add(flow_id)
        return group

    @staticmethod
    def group_by_query_id(flow_ids):
        group = dict()
        for flow_id in flow_ids:
            query_id = FlowData().get(flow_id).path_query_id
            if query_id not in group.keys():
                group[query_id] = list()
            group[query_id].append(flow_id)
        return group

    def get_non_reach_flow_ids(self, flow_ids):
        # Construct flow ids who haven't completed
        non_complete_flow_ids = []
        for flow_id in flow_ids:
            if flow_id not in self.path_query_complete_flow_ids:
                non_complete_flow_ids.append(flow_id)
        return non_complete_flow_ids

    def path_query(self, query_flow_ids):
        # Construct flow ids who haven't completed
        non_complete_flow_ids = self.get_non_reach_flow_ids(query_flow_ids)

        # Group by domain name
        flow_ids_by_domain_name = self.group_by_domain_name(non_complete_flow_ids)
        for domain_name in flow_ids_by_domain_name.keys():
            flow_ids = flow_ids_by_domain_name[domain_name]
            flow_ids_by_query_id = self.group_by_query_id(flow_ids)
            for query_id in flow_ids_by_query_id.keys():
                this_flow_ids = flow_ids_by_query_id[query_id]
                request_builder = RequestBuilder(
                    Definitions.QueryAction.ADD,
                    Definitions.QueryType.PATH_QUERY_TYPE,
                    query_id
                )
                for flow_id in this_flow_ids:
                    flow = FlowData().get(flow_id)
                    request_builder.add_item(flow, flow.last_hop)
                request_dict = request_builder.build()
                ThreadData().get_control_thread(domain_name).add_request(request_dict,
                                                                         callback=self.path_query_callback)

    def path_query_callback(self, request, response):
        to_query_flow_ids = []
        for item, hop_ip in list(zip(request["query-desc"], response)):
            flow_id = int(item["flow"]["flow-id"])
            hop_domain = DomainData().get_domain(hop_ip).domain_name
            hop = Hop(hop_domain, hop_ip)

            # Get flow object
            if not DomainData().has_ip(hop_ip):
                raise UnknownIP(hop_ip)
            flow = FlowData().get(flow_id)

            # If domain already in the flow, delete hop after it (including it)
            if flow.has_domain(hop_domain):
                flow.delete_path_after_hop(hop_domain)
            flow.path.append(hop)

            # Judge if the flow has reached the destination
            if flow.last_hop != "" and DomainData().has_ip(flow.last_hop()) and DomainData().get_domain(
                    flow.last_hop).domain_name == DomainData().get_domain(flow.dst_ip).domain_name:
                flow.path_query_complete = True
                self.path_query_complete_flow_ids.add(flow.id)

            if flow.path_query_complete is not True:
                to_query_flow_ids.append(flow.id)

        self.path_query(to_query_flow_ids)

    def resource_query_thread(self):
        # TODO
        pass

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
            flow_ids.union(set([
                FlowData().get_flow_id(i) for i in flows_of_jobs
            ]))
        return list(flow_ids)

    def run(self):
        # Get domain query id
        self.prepare()

        # Get all flows of the set of tasks
        self.flow_ids = self.get_flows(self.tasks)

        # Add every flow id to Query data store
        for flow_id in self.flow_ids:
            flow_obj = FlowData().get(flow_id)
            flow_obj.set_path_query_id(self._path_query_id)
            flow_obj.set_resource_query_id(self._resource_query_id)

        # Add completed flow ids to complete set
        for flow_id in self.flow_ids:
            flow = FlowData().get(flow_id)
            if flow.path_query_complete:
                self.path_query_complete_flow_ids.add(flow.id)

        # Do path query
        self.path_query(self.flow_ids)

        # waiting for all path query complete
        while len(self.path_query_complete_flow_ids) < len(self.flow_ids):
            time.sleep(Definitions.POLL_TIME)

        self.resource_query_thread()


class RequestBuilder(object):
    def __init__(self, action, query_type, query_id=None):
        self.action = action
        self.query_type = query_type
        if query_id is not None:
            self.query_id = query_id
        self.items = []

    def add_item(self, flow, ingress_point=None):
        item = {
            "flow": {
                "flow-id": flow.id,
                "src-ip": flow.src_ip,
                "src-port": flow.src_port,
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
            result["query-id"]: self.query_id
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
