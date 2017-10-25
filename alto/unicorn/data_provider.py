from itertools import chain
from threading import Thread, Lock


class SingletonType(type):
    def __call__(cls, *args, **kwargs):
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = super(SingletonType, cls).__call__(
                *args, **kwargs)
            return cls.__instance


class DomainData(metaclass=SingletonType):
    class Domain(object):
        def __init__(self):
            self.domain_name = ""
            self.update_url = ""
            self.control_url = ""
            self.hosts = list()
            self.ingress_point = ""
            self.lock = Lock()

        def get_from_dict(self, dic):
            if "domain_name" in dic:
                self.domain_name = dic["domain_name"]
            if "domain_update_url" in dic:
                self.update_url = dic["update-url"]
            if "domain_control_url" in dic:
                self.control_url = dic["control-url"]
            if "hosts" in dic:
                self.hosts = dic["hosts"]
            if "ingress-point" in dic:
                self.ingress_point = dic["ingress-point"]

    def __init__(self):
        super(DomainData, self).__init__()
        # domain name -> Domain object
        self.domains = {}

        # IP -> domain name
        self.ip2domain = {}

    def __iter__(self):
        for i in self.domains.keys():
            yield i

    def __contains__(self, item):
        return item in self.domains

    def __getitem__(self, item):
        # If exist, return element
        # Else raise KeyError
        return self.domains[item]

    def add(self, domain_name, data, callback=None):
        self.domains[domain_name] = DomainData.Domain()
        self.domains[domain_name].get_from_dict(data)
        for i in data["hosts"]:
            self.ip2domain[i] = domain_name
        for i in data["ingress-points"]:
            self.ip2domain[i] = domain_name
        if callback:
            thread = Thread(target=callback, args=[domain_name
                , self.domains[domain_name]])
            thread.start()

    def has_ip(self, ip):
        if ip in self.ip2domain:
            return True
        else:
            return False

    def ip_to_domain_name(self, ip):
        return self.ip2domain[ip]


class QueryData(metaclass=SingletonType):
    class Query(object):
        def __init__(self):
            self.query_id = dict()
            self.query_type = ""
            self.query_url = ""
            self.request = ""
            self.result = ""

    def __init__(self):
        super(QueryData, self).__init__()
        self.querys = dict()
        self.domain_to_client = dict()
        self.lock = Lock()
        self.next_client_query_id = 1

    def __getitem__(self, item):
        return self.querys[item]

    def __contains__(self, item):
        return item in self.querys

    def __iter__(self):
        for i in self.querys.keys():
            yield i

    def add_query_id(self, client_query_id, domain_name, domain_query_id):
        if client_query_id not in self.querys:
            self.querys[client_query_id] = QueryData.Query()
        self.querys[client_query_id].query_id[domain_name] = domain_query_id
        self.domain_to_client[(domain_name, domain_query_id)] = client_query_id

    def get_query_object(self, domain_name, domain_query_id, client_query_id=None):
        """
        :rtype: QueryData.Query
        """
        if client_query_id is None:
            client_query_id = self.domain_to_client[(domain_name, domain_query_id)]
            return self.querys[client_query_id]
        else:
            return self.querys[client_query_id]

    def get_next_client_query_id(self):
        self.next_client_query_id += 1
        return self.next_client_query_id - 1


class ThreadData(metaclass=SingletonType):
    def __init__(self):
        self.update_stream_threads = dict()
        self.control_stream_threads = dict()
        self.lock = Lock()

    def __contains__(self, item):
        return item in self.update_stream_threads or item in self.control_stream_threads

    def __iter__(self):
        for i in chain(self.update_stream_threads.values(), self.control_stream_threads.values()):
            yield i

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


class FlowData(metaclass=SingletonType):
    class Hop:
        def __init__(self):
            self.domain_name = None
            self.ip = None

    class Flow:
        def __init__(self):
            self.id = None
            self.path = []
            self.content = None
            self.query_id = None

        def __eq__(self, other):
            return self.content == other.content

        def get_last_hop(self):
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

    def __init__(self):
        self.id_flow = dict()
        self.content_flow = dict()
        self.next_id = 1
        self.lock = Lock()

    def __contains__(self, item):
        return item in self.id_flow.keys()

    def __iter__(self):
        for i in self.id_flow.values():
            yield i

    def get_id(self, flow):
        self.lock.acquire()
        if flow in self.content_flow.keys():
            self.lock.release()
            return self.content_flow[flow].id
        else:
            flow_obj = FlowData.Flow()
            flow_obj.id = self.next_id
            self.next_id += 1
            flow_obj.content = flow
            self.id_flow[flow_obj.id] = flow_obj
            self.content_flow[flow] = flow_obj
            self.lock.release()
            return flow_obj.id

    def has_id(self, id):
        return id in self.id_flow.keys()

    def get(self, identifier):
        """
        Get flow obj from identifier
        :param identifier: the identifier could be used to find obj
        :return: The flow object
        :rtype: FlowData.Flow
        """
        if type(identifier) == "tuple":
            return self.content_flow[identifier]
        else:
            return self.id_flow[id]


Flow = FlowData.Flow
Hop = FlowData.Hop
