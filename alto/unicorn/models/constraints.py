from threading import Lock

from alto.unicorn.models.flows import FlowDataProvider
from alto.unicorn.models.jobs import JobDataProvider


class Term(object):
    def __init__(self, flow_id, coefficient, job_id):
        self._flow = FlowDataProvider().get(flow_id)
        self._coefficient = coefficient
        self._job = JobDataProvider().get(job_id)

    @property
    def flow(self):
        return self._flow

    @property
    def coefficient(self):
        return self._coefficient

    @property
    def job(self):
        return self._job


class Constraint(object):
    def __init__(self, bound=0):
        self._terms = set()
        self._bound = bound
        self._lock = Lock()

    @property
    def terms(self):
        return self._terms

    @property
    def bound(self):
        return self._bound

    @terms.setter
    def terms(self, terms):
        with self._lock:
            self._terms = terms

    @bound.setter
    def bound(self, bound):
        with self._lock:
            self._bound = bound

    def add_term(self, term):
        """
        :type term: Term
        """
        with self._lock:
            self._terms.add(term)
