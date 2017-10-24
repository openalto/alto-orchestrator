from itertools import chain
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

    def add(self, domain_name, data):
        self.domains[domain_name] = DomainData.Domain()
        self.domains[domain_name].get_from_dict(data)
        for i in data["hosts"]:
            self.ip2domain[i] = domain_name
        for i in data["ingress-points"]:
            self.ip2domain[i] = domain_name

    def hasIp(self, ip):
        if ip in self.ip2domain:
            return True
        else:
            return False

    def ip2DomainName(self, ip):
        return self.ip2domain[ip]


class QueryData(metaclass=SingletonType):
    class Query(object):
        def __init__(self):
            self.query_id = 0
            self.query_type = ""
            self.query_url = ""
            self.domain_name = ""
            self.args = ""
            self.result = ""

    def __init__(self):
        super(QueryData, self).__init__()
        self.querys = dict()

    def __getitem__(self, item):
        return self.querys[item]

    def __contains__(self, item):
        return item in self.querys

    def __iter__(self):
        for i in self.querys.keys():
            yield i

    def generate_query_id(self, domain_name, domain_query_id):
        return "%s_%d" % (domain_name, domain_query_id)

    def get_query_object(self, domain_name, domain_query_id):
        """
        :rtype: QueryData.Query
        """
        query_id = self.generate_query_id(domain_name, domain_query_id)
        if query_id in self:
            return self.querys[query_id]
        else:
            self.querys[query_id] = QueryData.Query()
            return self.querys[query_id]


class ThreadData(metaclass=SingletonType):
    def __init__(self):
        self.update_stream_threads = dict()
        self.control_stream_threads = dict()

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
