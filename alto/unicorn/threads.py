import json
from queue import Queue
from threading import Thread, Lock

import requests
from sseclient import SSEClient

from .data_provider import QueryData, DomainData, ThreadData
from .exceptions import UnknownEventType
from .utils import update_queries


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
        query_object = QueryData().get_query_object(domain_name=self.domain_name, domain_query_id=query_id)
        query_object.result = response
        update_queries(query_object.query_type)

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
                update_thread = Thread(target=self.handle_update_event, args=[update_event, update_queries])
                update_thread.start()
            else:
                raise UnknownEventType(event)


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

    def add_requst(self, request):
        self.new_requests_lock.acquire()
        self.new_requests.put(request)
        self.new_requests_lock.release()

    def handle_request(self, request):
        response = requests.post(self.control_url)
        # TODO: check response

    def run(self):
        """Start the control stream thread"""
        something_to_do = False
        while not self.new_requests.empty():
            something_to_do = True
            request = self.get_request()
            self.handle_request(request)
        if something_to_do:
            pass
