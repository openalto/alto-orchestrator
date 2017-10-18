import json

import falcon
from jsonschema import validate

from . import TASKS_SCHEMA


class RegisterEntry(object):
    def __init__(self, config):
        pass

    def register(self, domain, base_url, **params):
        # Store the agent info into db
        pass

    def on_post(self, req, res):
        raw_data = req.stream.read()
        agent_info = json.loads(raw_data.decode('utf-8'))

        feedback = self.register(**agent_info)
        res.status = falcon.HTTP_200
        res.body = json.dumps(feedback)


class TasksEntry(object):
    def __init__(self):
        self.jobs = list()
        self.tasks = list()
        self.task2Jobs = dict()
        self.flows = dict()

    def _path_query(self, src_ip, dst_ip, src_port=None, dst_port=None):
        pass

    def group(self, tasks):
        """
        Given an array of tasks, return a dict from the domain name to grouped flows
        :return: a dict from domain name to grouped flows
        """
        pass

    def index(self, info):
        taskIndex = 0
        jobIndex = 0
        for task in info["tasks"]:
            task["index"] = taskIndex
            self.task2Jobs[taskIndex] = set()
            for job in task["jobs"]:
                job["index"] = jobIndex
                job["taskIndex"] = taskIndex

                flows_of_job = [(i["ip"], i["port"], j["ip"], j["port"], job["protocol"]) for i in job["potential_srcs"]
                                for j in job["potential_dsts"]]
                for flow in flows_of_job:
                    if flow not in self.flows:
                        self.flows[flow] = {"jobIndex": [jobIndex], "taskIndex": [taskIndex]}
                    else:
                        self.flows[flow]["jobIndex"].append(jobIndex)
                        self.flows[flow]["taskIndex"].append(taskIndex)

                self.jobs.append(jobIndex)
                self.task2Jobs[taskIndex].add(jobIndex)
                jobIndex += 1
            self.tasks.append(task)
            taskIndex += 1
        return info

    def on_post(self, req, res):
        raw_data = req.stream.read()
        info = json.loads(raw_data.decode('utf-8'))

        # Validate input with json schema
        validate(info, TASKS_SCHEMA)

        # Index the info
        info = self.index(info)

        # Reconstruct into into self.tasks, self.jobs, self.flows


        # Preprocess: Group flows with same domain
        flows = self.group(info)
