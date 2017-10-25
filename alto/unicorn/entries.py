import json

import falcon
from jsonschema import validate

from alto.unicorn.data_provider import DomainData, ThreadData
from alto.unicorn.schemas import TASKS_SCHEMA, REGISTRY_SCHEMA
from alto.unicorn.threads import TasksHandlerThread, UpdateStreamThread


class RegisterEntry(object):
    def __init__(self, *args, **kwargs):
        pass

    def register(self, info):
        # Store the agent info into db
        DomainData().add(info["domain_name"], info, callback=connect_to_server)
        return json.dumps({"message": "OK"})

    def on_post(self, req, res):
        raw_data = req.stream.read()
        agent_info = json.loads(raw_data.decode('utf-8'))

        validate(agent_info, REGISTRY_SCHEMA)

        feedback = self.register(agent_info)
        res.status = falcon.HTTP_200
        res.body = json.dumps(feedback)


class TasksEntry(object):
    def __init__(self, *args, **kwargs):
        self.jobs = list()
        self.tasks = list()
        self.task2Jobs = dict()
        self.flows = dict()

    def handle_task(self, task):
        # TODO
        pass

    def on_post(self, req, res):
        raw_data = req.stream.read()
        info = json.loads(raw_data.decode('utf-8'))

        # Validate input with json schema
        validate(info, TASKS_SCHEMA)

        thread = TasksHandlerThread()
        thread.start()


def connect_to_server(domain_name, domain_data):
    """
    :param domain_name: The name of the domain to connect
    :param domain_data: The data of the domain
    :type domain_data: DomainData.Domain
    """
    if not ThreadData().has_control_thread(domain_name):
        thread = UpdateStreamThread(domain_name, domain_data.update_url)
        thread.start()
