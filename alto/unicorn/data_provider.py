from threading import Lock


class SingletonType(type):
    def __call__(cls, *args, **kwargs):
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = super(SingletonType, cls).__call__(
                *args, **kwargs)
            return cls.__instance


class Domain(object):
    def __init__(self):
        self.domain_name = ""
        self.update_url = ""
        self.control_url = ""
        self.hosts = set()
        self.ingress_points = set()
        self._lock = Lock()

    def get_from_dict(self, dic):
        """
        :type dic: dict
        """
        print(dic)
        with self._lock:
            if "domain_name" in dic:
                self.domain_name = dic["domain_name"]
            if "update-url" in dic:
                self.update_url = dic["update-url"]
            if "control-url" in dic:
                self.control_url = dic["control-url"]
            if "hosts" in dic:
                self.hosts = set(dic["hosts"])
            if "ingress-points" in dic:
                self.ingress_points = set(dic["ingress-points"])


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


class Query(object):
    def __init__(self):
        self.query_id = 0
        self.query_type = ""
        self.query_url = ""
        self.request = ""
        self.response = ""


class QueryData(metaclass=SingletonType):
    """
    Basic Idea: (domain_name, query_id) -> query object
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
            query = Query()
            query.query_id = query_id
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
        self.update_stream_threads = dict()
        self.control_stream_threads = dict()
        self._lock = Lock()

    def has_update_thread(self, domain_name):
        return domain_name in self.update_stream_threads

    def has_control_thread(self, domain_name):
        return domain_name in self.control_stream_threads

    def get_update_thread(self, domain_name):
        return self.update_stream_threads[domain_name]

    def get_control_thread(self, domain_name):
        return self.control_stream_threads[domain_name]

    def add_update_thread(self, domain_name, thread):
        self.update_stream_threads[domain_name] = thread

    def add_control_thread(self, domain_name, thread):
        self.control_stream_threads[domain_name] = thread


class Hop:
    def __init__(self, domain_name=None, ip=None):
        self.domain_name = domain_name
        self.ip = ip


class Flow:
    def __init__(self):
        self.id = 0
        self.path = []
        self.src_ip = None
        self.dst_ip = None
        self.src_port = None
        self.dst_port = None
        self.protocol = None
        self._path_query_id = None
        self._resource_query_id = None
        self.path_query_complete = False
        self._lock = Lock()

    @property
    def last_hop(self):
        if self.path and len(self.path) > 0:
            return self.path[-1].ip
        else:
            return ""

    def has_domain(self, domain_name):
        for hop in self.path:
            if hop.domain_name == domain_name:
                return True
        return False

    def delete_path_after_hop(self, domain_name):
        index = -1
        for hop in self.path:
            if hop.domain_name == domain_name:
                index = self.path.index(hop)
        if index != -1:
            self.path = self.path[:index]

    @property
    def flow_tuple(self):
        return self.src_ip, self.src_port, self.dst_ip, self.dst_port, self.protocol

    @property
    def path_query_id(self):
        return self._path_query_id

    @property
    def resource_query_id(self):
        return self._resource_query_id

    def set_path_query_id(self, query_id):
        with self._lock:
            self._path_query_id = query_id

    def set_resource_query_id(self, query_id):
        with self._lock:
            self._resource_query_id = query_id


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
            flow_obj = Flow()
            flow_obj.id = self._next_id
            flow_obj.src_ip = flow[0]
            flow_obj.src_port = flow[1]
            flow_obj.dst_ip = flow[2]
            flow_obj.dst_port = flow[3]
            flow_obj.protocol = flow[4]

            # Add index to FlowData()
            self._id_flow[flow_obj.id] = flow_obj
            self._content_flow[flow] = flow_obj

            # End
            self._lock.release()
            self._next_id += 1
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
