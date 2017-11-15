import json

import falcon
from jsonschema import validate

from alto.unicorn.data_model import Domain
from alto.unicorn.data_provider import DomainDataProvider, ThreadDataProvider
from alto.unicorn.logger import logger
from alto.unicorn.models.hosts import HostDataProvider
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


class TaskLookupEntry(object):
    def on_get(self, req, res, task_id):
        res.status = falcon.HTTP_200
        try:
            task = TaskDataProvider().get_task_obj(int(task_id))
            res.body = json.dumps(task.to_dict())
        except KeyError:
            res.body = json.dumps({"error": "orchestrator doesn't have such task id"})


class PathCompleteLookupEntry(object):
    def on_get(self, req, res, task_id):
        try:
            task = TaskDataProvider().get_task_obj(int(task_id))
            res.body = json.dumps({
                "complete": task.path_query_latest,
                "timestamp": task.path_query_update_time
            })
        except KeyError:
            res.body = json.dumps({
                "complete": False,
                "timestamp": 0
            })


class ResourceQueryCompleteLookupEntry(object):
    def on_get(self, req, res, task_id):
        res.status = falcon.HTTP_200
        try:
            task = TaskDataProvider().get_task_obj(int(task_id))
            res.body = json.dumps({
                "complete": task.resource_query_complete,
                "timestamp": task.resource_query_update_time
            })
        except KeyError:
            res.body = json.dumps({
                "complete": False,
                "timestamp": 0
            })


class SchedulingCompleteLookupEntry(object):
    def on_get(self, req, res, task_id):
        res.status = falcon.HTTP_200
        try:
            task = TaskDataProvider().get_task_obj(int(task_id))
            res.body = json.dumps({
                "complete": task.scheduling_result_complete,
                "timestamp": task.scheduling_result_update_time
            })
        except KeyError:
            res.body = json.dumps({
                "complete": False,
                "timestamp": 0
            })


class ResourceLookupEntry(object):
    def on_get(self, req, res, task_id):
        res.status = falcon.HTTP_200
        try:
            task = TaskDataProvider().get_task_obj(int(task_id))
            task_dict = dict()
            handler_thread = task.task_handler_thread  # type: TasksHandlerThread
            resource_query_obj = handler_thread.resource_query_obj  # type: Query
            # task_dict["query-id"] = resource_query_obj.query_id
            domain_query_dict = resource_query_obj.domain_query
            for domain_name in domain_query_dict:
                task_dict[domain_name] = dict()
                task_dict[domain_name]["request"] = domain_query_dict[domain_name].to_list()
                task_dict[domain_name]["response"] = domain_query_dict[domain_name].response
            res.body = json.dumps(task_dict)
        except KeyError:
            res.body = json.dumps({"error": "orchestrator doesn't have such task id"})


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


class SchedulingResultLookupEntry(object):
    def on_get(self, req, res, task_id):
        res.status = falcon.HTTP_200
        try:
            task = TaskDataProvider().get_task_obj(int(task_id))
        except KeyError:
            res.body = json.dumps({"error": "orchestrator doesn't have such task id"})
            return
        scheduling_result = task.scheduling_result
        jobs = task.jobs
        task_dict = dict()
        for job in jobs:
            flows = job.flows
            job_dict = dict()
            for flow in flows:
                if flow.flow_id not in scheduling_result.keys():
                    continue
                job_dict[flow.flow_id] = flow.to_dict()
                job_dict[flow.flow_id]["avail-bw"] = scheduling_result[flow.flow_id]
            task_dict[job.job_id] = job_dict
        res.body = json.dumps(task_dict)


class ManagementIPLookupEntry(object):
    def on_get(self, req, res, ip):
        res.status = falcon.HTTP_200
        res.body = json.dumps({"management-ip": HostDataProvider().get_management_ip(ip)})


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
