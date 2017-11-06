from threading import Lock


class QueryItem(object):
    def __init__(self, flow_id, ingress_point):
        self._flow_id = 0
        self._ingress_point = ""

    @property
    def flow_id(self):
        return self._flow_id

    @property
    def ingress_point(self):
        return self._ingress_point


class DomainQuery(object):
    def __init__(self, query_id, domain_name):
        self.query_id = query_id
        self._domain_name = domain_name
        self._query_items = list()
        self._response = ""

    @property
    def domain_name(self):
        return self._domain_name

    @property
    def query_items(self):
        """
        :rtype: list[QueryItem]
        """
        return self._query_items

    @property
    def response(self):
        """
        :rtype: str
        """
        return self.response

    @response.setter
    def response(self, response):
        self._response = response

    def add_query_item(self, query_item):
        """
        :type query_item: QueryItem
        """
        self._query_items.append(query_item)


class Query(object):
    def __init__(self, query_id):
        self._query_id = query_id
        self._query_type = ""
        self._domain_query = dict()
        self._lock = Lock()

    @property
    def query_id(self):
        return self._query_id

    @property
    def query_type(self):
        return self._query_type

    @query_type.setter
    def query_type(self, query_type):
        self._query_type = query_type

    @property
    def domain_query(self):
        return self._domain_query

    @domain_query.setter
    def domain_query(self, domain_query):
        self._domain_query = domain_query

    def add(self, domain_query):
        """
        :type domain_query: DomainQuery
        """
        with self._lock:
            self._domain_query[domain_query.domain_name] = domain_query

    def get_domain_query(self, domain_name):
        """
        :rtype: DomainQuery
        """
        if domain_name not in self._domain_query:
            self._domain_query[domain_name] = DomainQuery(self._query_id, domain_name)
        return self._domain_query[domain_name]


class Domain(object):
    def __init__(self):
        self._domain_name = ""
        self._update_url = ""
        self._control_url = ""
        self._hosts = set()
        self._ingress_points = set()
        self._lock = Lock()

    @property
    def domain_name(self):
        return self._domain_name

    @property
    def update_url(self):
        return self._update_url

    @update_url.setter
    def update_url(self, update_url):
        with self._lock:
            self._update_url = update_url

    @property
    def control_url(self):
        return self._control_url

    @control_url.setter
    def control_url(self, control_url):
        with self._lock:
            self._control_url = control_url

    @property
    def hosts(self):
        return self._hosts

    @property
    def ingress_points(self):
        return self._ingress_points

    def get_from_dict(self, dic):
        """
        :type dic: dict
        """
        with self._lock:
            if "domain_name" in dic:
                self._domain_name = dic["domain_name"]
            if "update-url" in dic:
                self._update_url = dic["update-url"]
            if "control-url" in dic:
                self._control_url = dic["control-url"]
            if "hosts" in dic:
                self._hosts = set(dic["hosts"])
            if "ingress-points" in dic:
                self._ingress_points = set(dic["ingress-points"])


class Hop:
    def __init__(self, domain_name, ip):
        self._domain_name = domain_name
        self._ip = ip

    @property
    def domain_name(self):
        return self._domain_name

    @property
    def ip(self):
        return self._ip


class Flow:
    def __init__(self, id, src_ip, src_port, dst_ip, dst_port, protocol):
        self._id = id
        self._path = []
        self._src_ip = src_ip
        self._dst_ip = dst_ip
        self._src_port = src_port
        self._dst_port = dst_port
        self._protocol = protocol
        self._path_query_id = None
        self._resource_query_id = None
        self._path_query_complete = False
        self._lock = Lock()

    def path_query_complete(self):
        """
        Complete path query of this flow
        """
        self._path_query_complete = True

    @property
    def id(self):
        return self._id

    @property
    def last_hop(self):
        """
        Get IP of the last hop
        :return: the IP of the last hop
        :rtype: str
        """
        if self.path and len(self.path) > 0:
            return self.path[-1].ip
        else:
            return ""

    @property
    def src_ip(self):
        """
        :rtype: str
        """
        return self._src_ip

    @property
    def src_port(self):
        """
        :rtype: int
        """
        return self.src_port

    @property
    def dst_ip(self):
        """
        :rtype: str
        """
        return self._dst_ip

    @property
    def dst_port(self):
        """
        :rtype: int
        """
        return self._dst_port

    @property
    def protocol(self):
        """
        :rtype: str
        """
        return self._protocol

    def has_domain(self, domain_name):
        """
        Check if the flow through a domain
        :param domain_name: the named of the query domain
        :return: If there is a hop in the domain
        :rtype: bool
        """
        for hop in self.path:
            if hop.domain_name == domain_name:
                return True
        return False

    def delete_path_after_hop(self, domain_name):
        """
        Delete path after a hop (including this hop)
        :param domain_name: the domain name of the hop
        """
        index = -1
        for hop in self.path:
            if hop.domain_name == domain_name:
                index = self.path.index(hop)
        if index != -1:
            self.path = self.path[:index]

    @property
    def flow_tuple(self):
        return self._src_ip, self._src_port, self._dst_ip, self._dst_port, self._protocol

    @property
    def path_query_id(self):
        return self._path_query_id

    @property
    def resource_query_id(self):
        return self._resource_query_id

    @path_query_id.setter
    def path_query_id(self, query_id):
        with self._lock:
            self._path_query_id = query_id

    @resource_query_id.setter
    def resource_query_id(self, query_id):
        with self._lock:
            self._resource_query_id = query_id
