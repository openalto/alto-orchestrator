from threading import Lock

from alto.unicorn.models.flows import Flow
from alto.unicorn.models.singleton import SingletonType


class Job(object):
    _next_id = 1
    _static_lock = Lock()

    @staticmethod
    def gen_id(job):
        JobDataProvider().add(Job._next_id, job)
        Job._next_id += 1
        return Job._next_id - 1

    def __init__(self, file_size):
        """
        :type file_size: int
        """
        self._job_id = Job.gen_id(self)
        self._file_size = file_size
        self._flows = dict()  # type: dict[int, Flow]

    @property
    def job_id(self):
        return self._job_id

    @property
    def file_size(self):
        return self._file_size

    @property
    def flows(self):
        """
        :rtype: set[Flow]
        :return:
        """
        return set(self._flows.values())

    def add_flow(self, flow):
        """
        :type flow: Flow
        """
        self._flows[flow.flow_id] = flow

    def has_flow_id(self, flow_id):
        return flow_id in self._flows.keys()

    def get_flow(self, flow_id):
        if self.has_flow_id(flow_id):
            return self._flows[flow_id]
        else:
            raise KeyError

    def to_dict(self):
        result = dict()
        result["job-id"] = self._job_id
        result["flows"] = dict()
        for flow in self.flows:
            result["flows"][flow.flow_id] = flow.to_dict()
        return result


class JobDataProvider(metaclass=SingletonType):
    def __init__(self):
        self._jobs = dict()  # type: dict[int, Job]
        pass

    def get(self, job_id):
        return self._jobs[job_id]

    def add(self, job_id, job):
        self._jobs[job_id] = job
