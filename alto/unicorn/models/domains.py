import itertools
from threading import Lock

from alto.unicorn.models.hosts import Host
from alto.unicorn.models.singleton import SingletonType


class Domain(object):
    def __init__(self, domain_name):
        self._domain_name = domain_name
        self._update_url = ""
        self._control_url = ""
        self._deploy_url = ""
        self._hosts = list()  # type: list[Host]
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
    def deploy_url(self):
        return self._deploy_url

    @deploy_url.setter
    def deploy_url(self, url):
        self._deploy_url = url

    @property
    def control_url(self):
        return self._control_url

    @control_url.setter
    def control_url(self, control_url):
        with self._lock:
            self._control_url = control_url

    @property
    def hosts(self):
        """
        :rtype: list[Host]
        """
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
            if "deploy-url" in dic:
                self._deploy_url = dic["deploy-url"]
            if "hosts" in dic:
                for host in dic["hosts"]:
                    self._hosts.append(Host(host["host-ip"], host["management-ip"]))
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
        domain = Domain(domain_name)
        domain.get_from_dict(data)
        self._domains[domain_name] = domain
        for i in domain.hosts:
            self._ip2domain[i.host_ip] = domain
        for i in domain.ingress_points:
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
