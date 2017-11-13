from threading import Lock

from alto.unicorn.models.domains import DomainDataProvider
from .singleton import SingletonType


class Hop:
    def __init__(self, ip):
        self._ip = ip

    @property
    def domain_name(self):
        return DomainDataProvider().get_domain(self._ip).domain_name

    @property
    def ip(self):
        return self._ip


class Flow:
    def __init__(self, flow_id, src_ip, src_port, dst_ip, dst_port, protocol):
        self._flow_id = flow_id  # type: int
        self._path = list()  # type: list[Hop]
        self._src_ip = src_ip  # type: str
        self._dst_ip = dst_ip  # type: str
        self._src_port = src_port  # type: int
        self._dst_port = dst_port  # type: int
        self._protocol = protocol  # type: str
        self._path_query_id = None  # type: int
        self._is_complete = False  # type: bool
        self._lock = Lock()

        self._job_id = 0

    @property
    def flow_id(self):
        return self._flow_id

    @property
    def through_domains(self):
        domains = list()  # type: list[str]
        domains.append(DomainDataProvider().get_domain(self._src_ip).domain_name)
        domains.extend([hop.domain_name for hop in self._path])
        return domains

    def get_ingress_point(self, domain_name):
        through_domains = self.through_domains
        index = through_domains.index(domain_name)
        if index == 0:
            return ""
        else:
            return self._path[index-1].ip

    def get_egress_point(self, domain_name):
        through_domains = self.through_domains
        index = through_domains.index(domain_name)
        if index == len(through_domains) - 1:
            return ""
        else:
            return self._path[index].ip

    @property
    def last_hop(self):
        """
        Get IP of the last hop
        :return: the IP of the last hop
        :rtype: str
        """
        if self._path and len(self._path) > 0:
            return self._path[-1].ip
        else:
            return ""

    @property
    def src_ip(self):
        return self._src_ip

    @property
    def src_port(self):
        return self._src_port

    @property
    def dst_ip(self):
        return self._dst_ip

    @property
    def dst_port(self):
        return self._dst_port

    @property
    def protocol(self):
        return self._protocol

    @property
    def is_complete(self):
        return self._is_complete

    def complete(self):
        with self._lock:
            self._is_complete = True

    @property
    def path(self):
        return self._path

    def has_domain(self, domain_name):
        """
        Check if the flow through a domain
        :param domain_name: the named of the query domain
        :return: If there is a hop in the domain
        :rtype: bool
        """
        for hop in self._path:
            if hop.domain_name == domain_name:
                return True
        return False

    def delete_path_after_hop(self, domain_name):
        """
        Delete path after a hop (not including this hop)
        :param domain_name: the domain name of the hop
        """
        index = -1
        for hop in self._path:
            if hop.domain_name == domain_name:
                index = self._path.index(hop)
        if index != -1:
            self._path = self._path[:index+1]

    @property
    def flow_tuple(self):
        return self._src_ip, self._src_port, self._dst_ip, self._dst_port, self._protocol

    @property
    def path_query_id(self):
        return self._path_query_id

    @path_query_id.setter
    def path_query_id(self, query_id):
        with self._lock:
            self._path_query_id = query_id

    def add_hop(self, hop_ip):
        """
        :type hop_ip: str
        :param hop_ip:
        """
        hop = Hop(hop_ip)
        self._path.append(hop)

    @property
    def job_id(self):
        return self._job_id

    @job_id.setter
    def job_id(self, job_id):
        self._job_id = job_id

    def to_dict(self):
        result = dict()
        result["flow_id"] = self.flow_id
        result["complete"] = self.is_complete
        result["path"] = [hop.ip for hop in self.path]
        result["protocol"] = self.protocol
        result["src-ip"] = self._src_ip
        if self._src_port:
            result["src-port"] = self._src_port
        result["dst-ip"] = self._dst_ip
        if self._dst_port:
            result["dst-port"] = self._dst_port
        return result


class FlowDataProvider(metaclass=SingletonType):
    """
    Basic Idea: (5-tuple flow) -> flow obj
    flow id -> flow obj
    """

    def __init__(self):
        super(FlowDataProvider, self).__init__()
        self._id_flow = dict()
        self._content_flow = dict()
        self._next_id = 1
        self._lock = Lock()

    def get_flow_id(self, flow):
        self._lock.acquire()
        if flow in self._content_flow.keys():
            self._lock.release()
            return self._content_flow[flow].flow_id
        else:
            # Create a new flow
            flow_obj = Flow(self._next_id, flow[0], flow[1], flow[2], flow[3], flow[4])

            # Add index to FlowData()
            self._id_flow[flow_obj.flow_id] = flow_obj
            self._content_flow[flow] = flow_obj

            # End
            self._next_id += 1
            self._lock.release()
            return flow_obj.flow_id

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
            return self._id_flow[identifier]

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
                flow = FlowDataProvider().get(flow_id)
                if flow.path_query_id is None:
                    result_ids.append(flow_id)
                    flow.path_query_id = path_query_id
        return result_ids
