import json
import time
from queue import Queue
from threading import Thread, Lock

import requests
from sseclient import SSEClient

from alto.unicorn.data_provider import QueryData, DomainData, ThreadData, FlowData
from alto.unicorn.definitions import Definitions
from alto.unicorn.exceptions import UnknownEventType


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
            hop = FlowData.Hop()
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
            callback(resp, *args)

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
    def __init__(self):
        super(TasksHandlerThread, self).__init__()
        self.flows = None
        self.path_query_flows = list()
        self.resource_query_flows = list()
        self.completed_flows = list()
        self.path_query_lock = Lock()
        self.resource_query_lock = Lock()

    @staticmethod
    def group_by_domain_name(flows):
        group = dict()
        for flow in flows:
            last_hop = flow.get_last_hop()
            ip = last_hop if last_hop != "" else flow.content[0]  # Source IP / Last hop ip
            domain_name = DomainData().ip_to_domain_name(ip)
            if domain_name not in group:
                group[domain_name] = list()
            group[domain_name].add(flow)
        return group

    @staticmethod
    def group_by_query_id(flows):
        group = dict()
        for flow in flows:
            if flow.query_id not in group:
                group[flow.query_id] = list()
            group[flow.query_id].add(flow)
        return group

    def path_query_thread(self):
        while True:
            if len(self.path_query_flows) > 0:

                # Group path query flows by query id
                self.path_query_lock.acquire()
                flows_by_query_id = self.group_by_query_id(self.path_query_flows)
                self.path_query_flows = list()
                self.path_query_lock.release()

                for query_id in flows_by_query_id.keys():
                    flows_by_domain_name = self.group_by_domain_name(flows_by_query_id[query_id])
                    for domain_name in flows_by_domain_name.keys():
                        flows = flows_by_domain_name[domain_name]
                        request_builder = RequestBuilder(
                            Definitions.QueryAction.ADD,
                            Definitions.QueryType.PATH_QUERY_TYPE,
                            query_id
                        )
                        for flow in flows:
                            request_builder.add_item(flow, flow.get_last_hop())
                        request_dict = request_builder.build()
                        ThreadData().get_control_thread(domain_name).add_request(request_dict)

    def resource_query_thread(self):
        # TODO
        pass

    def run(self):
        path_thread = Thread(target=self.path_query_thread, args=[])
        path_thread.start()
        resource_thread = Thread(target=self.resource_query_thread, args=[])
        resource_thread.start()


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


class PrepareThread(Thread):
    def __init__(self, tasks):
        super(PrepareThread, self).__init__()
        self.tasks = tasks

    def run(self):
        client_path_query_id = QueryData().get_next_client_query_id()
        for domain_name in DomainData():
            control_thread = ThreadData().get_control_thread(domain_name)
            request_builder = RequestBuilder(
                Definitions.QueryAction.NEW,
                Definitions.QueryType.PATH_QUERY_TYPE
            )
            request = request_builder.build()
            control_thread.add_request(request, self.add_query_id, domain_name, client_path_query_id)
        client_resource_query_id = QueryData().get_next_client_query_id()
        for domain_name in DomainData():
            control_thread = ThreadData().get_control_thread(domain_name)
            request_builder = RequestBuilder(
                Definitions.QueryAction.NEW,
                Definitions.QueryType.RESOURCE_QUERY_TYPE
            )
            request = request_builder.build()
            control_thread.add_request(request, self.add_query_id, domain_name, client_resource_query_id)

    def add_query_id(self, response, domain_name, client_query_id):
        domain_query_id = response["query-id"]
        QueryData().add_query_id(client_query_id, domain_name, domain_query_id)


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
