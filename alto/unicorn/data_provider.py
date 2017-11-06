from threading import Lock

from alto.unicorn.data_model import Domain, Query, Flow


class SingletonType(type):
    def __call__(cls, *args, **kwargs):
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = super(SingletonType, cls).__call__(
                *args, **kwargs)
            return cls.__instance


class DomainData(metaclass=SingletonType):
    def __init__(self):
        super(DomainData, self).__init__()
        # domain name -> Domain object
        self._domains = {}

        # IP -> domain name
        self._ip2domain = {}

    def __iter__(self):
        for i in self._domains.keys():
            yield i

    def __getitem__(self, item):
        """
        :rtype: Domain
        """
        return self._domains[item]

    def add(self, domain_name, data, callback=None):
        """
        :type domain_name: str
        :type data: dict
        """
        domain = Domain()
        self._domains[domain_name] = domain
        domain.get_from_dict(data)
        for i in data["hosts"]:
            self._ip2domain[i] = domain
        for i in data["ingress-points"]:
            self._ip2domain[i] = domain

        if callback:
            callback(domain_name, domain)

    def has_ip(self, ip):
        """
        :rtype: bool
        """
        return ip in self._ip2domain

    def get_domain(self, ip):
        """
        :rtype: Domain
        """
        return self._ip2domain[ip]


class QueryData(metaclass=SingletonType):
    """
    Basic Idea: path query_id -> query object
    """

    def __init__(self):
        super(QueryData, self).__init__()

        # Query id -> Query Object
        self._queries = dict()

        self._next_id = 1

        self._lock = Lock()

    def gen_query_id(self):
        """
        Generate a query id and add it to data store
        :rtype: int
        """
        self._add_query_id(self._next_id)
        with self._lock:
            self._next_id += 1
        return self._next_id - 1

    def _add_query_id(self, query_id):
        """
        :type query_id: int
        """
        with self._lock:
            query = Query(query_id)
            self._queries[query_id] = query

    def get(self, query_id=None):
        """
        :type query_id: int
        :rtype: Query
        """
        if query_id is not None:
            return self._queries[query_id]
        raise KeyError


class ThreadData(metaclass=SingletonType):
    def __init__(self):
        self._update_stream_threads = dict()
        self._control_stream_threads = dict()
        self._task_handler_threads = dict()
        self._lock = Lock()

    def has_update_thread(self, domain_name):
        return domain_name in self._update_stream_threads

    def has_control_thread(self, domain_name):
        return domain_name in self._control_stream_threads

    def has_task_handler_thread(self, query_id):
        return query_id in self._task_handler_threads

    def get_update_thread(self, domain_name):
        return self._update_stream_threads[domain_name]

    def get_control_thread(self, domain_name):
        return self._control_stream_threads[domain_name]

    def get_task_handler_thread(self, query_id):
        return self._task_handler_threads[query_id]

    def add_update_thread(self, domain_name, thread):
        self.remove_update_thread(domain_name)
        with self._lock:
            self._update_stream_threads[domain_name] = thread

    def add_control_thread(self, domain_name, thread):
        self.remove_control_thread(domain_name)
        with self._lock:
            self._control_stream_threads[domain_name] = thread

    def add_task_handler_thread(self, query_id, thread):
        self.remove_task_handler_thread(query_id)
        with self._lock:
            self._task_handler_threads[query_id] = thread

    def remove_update_thread(self, domain_name):
        if self.has_update_thread(domain_name):
            with self._lock:
                del self._update_stream_threads[domain_name]

    def remove_control_thread(self, domain_name):
        if self.has_control_thread(domain_name):
            with self._lock:
                del self._control_stream_threads[domain_name]

    def remove_task_handler_thread(self, query_id):
        if self.has_task_handler_thread(query_id):
            with self._lock:
                del self._task_handler_threads[query_id]


class FlowData(metaclass=SingletonType):
    """
    Basic Idea: (5-tuple flow) -> flow obj
    flow id -> flow obj
    """

    def __init__(self):
        self._id_flow = dict()
        self._content_flow = dict()
        self._next_id = 1
        self._lock = Lock()

    def get_flow_id(self, flow):
        self._lock.acquire()
        if flow in self._content_flow.keys():
            self._lock.release()
            return self._content_flow[flow].id
        else:
            # Create a new flow
            flow_obj = Flow(self._next_id, flow[0], flow[1], flow[2], flow[3], flow[4])

            # Add index to FlowData()
            self._id_flow[flow_obj.id] = flow_obj
            self._content_flow[flow] = flow_obj

            # End
            self._next_id += 1
            self._lock.release()
            return flow_obj.id

    def has_id(self, id):
        return id in self._id_flow.keys()

    def get(self, identifier):
        """
        Get flow obj from identifier
        :param identifier: the identifier could be used to find obj
        :return: The flow object
        :rtype: Flow
        """
        if type(identifier) == "tuple":
            return self._content_flow[identifier]
        else:
            return self._id_flow[id]

    def get_flows_without_path_query_id(self, flow_ids, path_query_id):
        """
        Get flow ids without path query id, and set them to the id
        :param flow_ids:
        :param path_query_id:
        :return:
        """
        result_ids = list()
        with self._lock:
            for flow_id in flow_ids:
                flow = FlowData().get(flow_id)
                if flow.path_query_id is None:
                    result_ids.append(flow_id)
                    flow.path_query_id = path_query_id
        return result_ids
