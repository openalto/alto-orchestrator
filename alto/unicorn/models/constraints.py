from threading import Lock

from alto.unicorn.models.flows import FlowDataProvider, Flow
from alto.unicorn.models.jobs import JobDataProvider, Job


class Term(object):
    def __init__(self, flow_id, coefficient, job_id):
        self._flow = FlowDataProvider().get(flow_id)  # type: Flow
        self._coefficient = coefficient
        self._job = JobDataProvider().get(job_id)  # type: Job

    @property
    def flow(self):
        return self._flow

    @property
    def coefficient(self):
        return self._coefficient

    @property
    def job(self):
        return self._job

    def __repr__(self):
        return "<flow:%s>" % self.flow.flow_id


class Constraint(object):
    def __init__(self, bound=0):
        self._terms = set()  # type: set[Term]
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

    def __repr__(self):
        return ' + '.join([str(t) for t in self.terms]) + ' <= ' + str(self.bound)
