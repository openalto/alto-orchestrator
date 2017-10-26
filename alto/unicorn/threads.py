import json
import time
from queue import Queue
from threading import Thread, Lock

import requests
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
        response = requests.get(self.update_url, stream=True)
        return SSEClient(response)

    def start_control_stream_thread(self, control_url):
        """Start control stream"""
        control_stream_thread = ControlStreamThread(self.domain_name, control_url)
        control_stream_thread.start()

    def handle_update_event(self, update_event, callback):
        """Handle update event received from server"""
        query_id = update_event["query-id"]
        response = update_event["response"]
        query_obj = QueryData().get_query_object(domain_name=self.domain_name, domain_query_id=query_id)
        query_obj.result = response
        callback(query_obj)

    def run(self):
        """ Start the update stream thread """

        # Send a request to remote
        client = self.get_sseclient()

        # handle every received event
        for event in client.events():
            if event.event == "application/updatestreamcontrol":
                control_stream_url = json.loads(event.data)["control-uri"]
                DomainData()[self.domain_name].control_url = control_stream_url
            elif event.event == "application/json":
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
            time.sleep(0.3)


class TasksHandlerThread(Thread):
    def __init__(self, tasks):
        super(TasksHandlerThread, self).__init__()
        self.flow_ids = list()
        self.tasks = tasks
        self.path_query_complete_flow_ids = set()

    def prepare(self):
        for domain_name in DomainData():
            control_thread = ThreadData().get_control_thread(domain_name)
            request_builder = RequestBuilder(
                Definitions.QueryAction.NEW,
                Definitions.QueryType.PATH_QUERY_TYPE
            )
            request = request_builder.build()
            control_thread.add_request(request, self.add_query_id, domain_name)

            request_builder = RequestBuilder(
                Definitions.QueryAction.NEW,
                Definitions.QueryType.RESOURCE_QUERY_TYPE,
            )
            request = request_builder.build()
            control_thread.add_request(request, self.add_query_id, domain_name)

    @staticmethod
    def add_query_id(request, response, domain_name):
        query_id = response["query-id"]
        QueryData().add_query_id(domain_name, query_id)

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
    def group_by_query_id(flow_ids, domain_name):
        group = dict()
        for flow_id in flow_ids:
            query_id = QueryData().get_query_id(domain_name, flow_id)
            if query_id not in group.keys():
                group[query_id] = list()
            group[query_id].append(flow_id)
        return group

    def path_query(self):
        # Construct flow ids who haven't completed
        non_complete_flow_ids = []
        for flow_id in self.flow_ids:
            if flow_id not in self.path_query_complete_flow_ids:
                non_complete_flow_ids.append(flow_id)

        # Group by domain name
        flow_ids_by_domain_name = self.group_by_domain_name(self.flow_ids)
        for domain_name in flow_ids_by_domain_name.keys():
            flow_ids = flow_ids_by_domain_name[domain_name]
            flow_ids_by_query_id = self.group_by_query_id(flow_ids, domain_name)
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
                ThreadData().get_control_thread(domain_name).add_request(request_dict)

    def path_query_callback(self, request, response):
        for item, hop_ip in list(zip(request["query-desc"], response)):
            flow_id = int(item["flow"]["flow-id"])
            hop_domain = DomainData().get_domain(hop_ip).domain_name
            hop = Hop(hop_domain, hop_ip)

            # Get flow object
            if not DomainData().has_ip(hop_ip):
                raise UnknownIP(hop_ip)
            flow = FlowData().get(flow_id)

            if flow.has_domain(hop_domain):
                flow.delete_path_after_hop(hop_domain)
            flow.path.append(hop)
            if flow.get_last_hop() != "" and DomainData().has_ip(flow.get_last_hop()) and DomainData().get_domain_name(
                    flow.get_last_hop()) == DomainData().get_domain_name(flow.content[3]):
                flow.path_query_complete = True
            self.path_query_complete_flow_ids.add(flow.id)

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

        # Add completed flow ids to complete set
        for flow_id in self.flow_ids:
            flow = FlowData().get(flow_id)
            if flow.path_query_complete:
                self.path_query_complete_flow_ids.add(flow.id)

        # Do path query
        self.path_query()

        # TODO: waiting for all path query complete


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
                "src-ip": flow.content[0],
                "src-port": flow.content[1],
                "dst-ip": flow.content[2],
                "dst-port": flow.content[3],
                "protocol": flow.content[4]
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
