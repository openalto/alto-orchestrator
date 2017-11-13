from alto.unicorn.models.jobs import Job
from alto.unicorn.models.singleton import SingletonType


class Task(object):
    _next_id = 1

    @staticmethod
    def _gen_id():
        Task._next_id += 1
        return Task._next_id - 1

    def __init__(self, task_content):
        self._jobs = list()  # type: list[Job]
        self._task_id = Task._gen_id()
        self._task_content = task_content
        TaskDataProvider().add_task(self)

    def add_job(self, job):
        self._jobs.append(job)

    def to_dict(self):
        result = dict()
        result["task_id"] = self._task_id
        result["jobs"] = dict()
        for job in self.jobs:
            result["jobs"][job.job_id] = job.to_dict()
        return result

    @property
    def task_id(self):
        return self._task_id

    @property
    def jobs(self):
        return self._jobs

    @property
    def task_content(self):
        return self._task_content


class TaskDataProvider(metaclass=SingletonType):
    def __init__(self):
        super(TaskDataProvider, self).__init__()
        self._id_tasks = dict()

    @property
    def tasks(self):
        """
        :rtype: list[Task]
        :return:
        """
        return list(self._id_tasks.values())

    def add_task(self, task):
        self._id_tasks[task.task_id] = task

    def has_task_id(self, task_id):
        return task_id in self._id_tasks

    def get_task_obj(self, task_id):
        return self._id_tasks[task_id]
