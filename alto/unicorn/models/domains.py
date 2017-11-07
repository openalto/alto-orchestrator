from threading import Lock

from alto.unicorn.models.singleton import SingletonType


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


class DomainDataProvider(metaclass=SingletonType):
    def __init__(self):
        super(DomainDataProvider, self).__init__()
        # domain name -> Domain object
        self._domains = {}

        # IP -> domain name
        self._ip2domain = {}

    def __iter__(self):
        """
        :rtype: Domain
        """
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
