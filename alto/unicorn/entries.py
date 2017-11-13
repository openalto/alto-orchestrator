import json

import falcon
from jsonschema import validate

from alto.unicorn.data_model import Domain
from alto.unicorn.data_provider import DomainDataProvider, ThreadDataProvider
from alto.unicorn.logger import logger
from alto.unicorn.models.queries import Query
from alto.unicorn.models.tasks import TaskDataProvider
from alto.unicorn.schemas import TASKS_SCHEMA, REGISTRY_SCHEMA
from alto.unicorn.threads import TasksHandlerThread, UpdateStreamThread


class RegisterEntry(object):
    def __init__(self, *args, **kwargs):
        pass

    def register(self, info):
        # If the domain is already exists
        if info["domain-name"] in DomainDataProvider():
            pass
            # TODO

        # Store the agent info into db
        DomainDataProvider().add(info["domain-name"], info, callback=connect_to_server)
        return {"message": "OK"}

    def on_post(self, req, res):
        raw_data = req.stream.read()
        agent_info = json.loads(raw_data.decode('utf-8'))

        validate(agent_info, REGISTRY_SCHEMA)

        feedback = self.register(agent_info)
        res.status = falcon.HTTP_200
        res.body = json.dumps(feedback)


class TasksEntry(object):
    def __init__(self, *args, **kwargs):
        pass

    def on_post(self, req, res):
        raw_data = req.stream.read()
        info = json.loads(raw_data.decode('utf-8'))

        # Validate input with json schema
        validate(info, TASKS_SCHEMA)

        thread = TasksHandlerThread(info)
        thread.start()


class TasksLookupEntry(object):
    def on_get(self, req, res):
        res.status = falcon.HTTP_200
        tasks = TaskDataProvider().tasks
        result = dict()
        for task in tasks:
            result[task.task_id] = task.to_dict()
        res.body = json.dumps(result)


class ResourcesLookupEntry(object):
    def on_get(self, req, res):
        res.status = falcon.HTTP_200
        tasks = TaskDataProvider().tasks
        result = dict()
        for task in tasks:
            task_dict = dict()
            handler_thread = task.task_handler_thread  # type: TasksHandlerThread
            resource_query_obj = handler_thread.resource_query_obj  # type: Query
            task_dict["query-id"] = resource_query_obj.query_id
            domain_query_dict = resource_query_obj.domain_query
            for domain_name in domain_query_dict:
                task_dict[domain_name] = dict()
                task_dict[domain_name]["request"] = domain_query_dict[domain_name].to_list()
                task_dict[domain_name]["response"] = domain_query_dict[domain_name].response
            result[task.task_id] = task_dict
        res.body = json.dumps(result)


def connect_to_server(domain_name, domain_data):
    """
    :param domain_name: The name of the domain to connect
    :param domain_data: The data of the domain
    :type domain_data: Domain
    """
    if not ThreadDataProvider().has_update_thread(domain_name):
        logger.info("Start update stream: " + domain_data.update_url)
        thread = UpdateStreamThread(domain_name, domain_data.update_url)
        thread.start()
