from alto.unicorn.models.jobs import Job
from alto.unicorn.models.singleton import SingletonType


class Task(object):
    _next_id = 1

    @staticmethod
    def _gen_id():
        Task._next_id += 1
        return Task._next_id - 1

    def __init__(self, task_content, task_handler_thread=None):
        self._jobs = list()  # type: list[Job]
        self._task_id = Task._gen_id()
        self._task_content = task_content
        self._task_handler_thread = task_handler_thread
        TaskDataProvider().add_task(self)

    def add_job(self, job):
        self._jobs.append(job)

    def to_dict(self):
        result = dict()
        result["task-id"] = self._task_id
        result["jobs"] = dict()
        for job in self.jobs:
            result["jobs"][job.job_id] = job.to_dict()
        return result

    @property
    def task_handler_thread(self):
        return self._task_handler_thread

    @property
    def task_id(self):
        return self._task_id

    @property
    def jobs(self):
        return self._jobs

    @property
    def task_content(self):
        return self._task_content

    @property
    def path_query_latest(self):
        return self._task_handler_thread.path_query_latest

    @property
    def path_query_update_time(self):
        return self._task_handler_thread.path_query_update_time

    @property
    def resource_query_complete(self):
        return self._task_handler_thread.resource_query_complete

    @property
    def resource_query_update_time(self):
        return self._task_handler_thread.resource_query_update_time

    @property
    def scheduling_result_update_time(self):
        return self._task_handler_thread.scheduling_result_update_time

    @property
    def scheduling_result_complete(self):
        return self._task_handler_thread.scheduling_result_complete

    @property
    def scheduling_result(self):
        return self._task_handler_thread.scheduling_result


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
        """
        :rtype: Task
        """
        return self._id_tasks[task_id]
