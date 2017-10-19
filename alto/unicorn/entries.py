import json

import falcon
from jsonschema import validate

from . import TASKS_SCHEMA
from .data_provider import DomainsData, PathQueryData
from .threads import PathQueryThread


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

    def group(self):
        """
        :return: a dict from domain name to grouped flows
        """
        grouped_flows = dict()
        for flow in self.flows.keys():
            src_ip = flow[0]
            domain_name = DomainsData().ip2DomainName(src_ip)
            if domain_name not in grouped_flows:
                grouped_flows[domain_name] = set()
            grouped_flows[domain_name].add(flow)
        return grouped_flows

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

    def _path_query(self, grouped_flows):
        threads = set()
        PathQueryData().clear()
        while len(PathQueryData().reachedFlow) < len(grouped_flows):
            threads.clear()
            for domain_name in grouped_flows.keys():
                flows = grouped_flows[domain_name]
                thread = PathQueryThread(domain_name, flows)
                threads.add(thread)
                thread.start()
            for thread in threads:
                thread.join()
            query_result = PathQueryData().flowsPath
            for flow in query_result.keys():
                if self.isFlowReached(flow):
                    PathQueryData().addReachedFlow(flow)
                    # TODO: flow reach

    def isFlowReached(self, flow):
        if not PathQueryData().hasFlowFetched(flow):
            return False
        last_hop = PathQueryData().getLastHop(flow)
        domain_name = DomainsData().ip2DomainName(last_hop)
        dst_name = DomainsData().ip2DomainName(flow[2])  # flow[2] is dst-ip
        return domain_name == dst_name

    def on_post(self, req, res):
        raw_data = req.stream.read()
        info = json.loads(raw_data.decode('utf-8'))

        # Validate input with json schema
        validate(info, TASKS_SCHEMA)

        # Reconstruct into into self.tasks, self.jobs, self.flows
        info = self.index(info)

        # Preprocess: Group flows with same domain
        grouped_flows = self.group()

        # Send request - Path Query
        self._path_query(grouped_flows)

        # 1
