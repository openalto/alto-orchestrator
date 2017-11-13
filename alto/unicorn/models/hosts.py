from alto.unicorn.models.singleton import SingletonType


class Host(object):
    def __init__(self, host_ip, management_ip):
        self._host_ip = host_ip
        self._management_ip = management_ip
        HostDataProvider().add_host(self)

    def __eq__(self, other):
        return True if self.host_ip == other.host_ip and self.management_ip == other.management_ip else False

    @property
    def host_ip(self):
        return self._host_ip

    @property
    def management_ip(self):
        return self._management_ip


class HostDataProvider(metaclass=SingletonType):
    def __init__(self):
        self._host_ip_obj = dict()  # type: dict[str, Host]

    @property
    def host_ips(self):
        return list(self._host_ip_obj.keys())

    @property
    def hosts(self):
        return list(self._host_ip_obj.values())

    def has_host_ip(self, host_ip):
        return host_ip in self._host_ip_obj

    def get_host_obj(self, host_ip):
        return self._host_ip_obj[host_ip]

    def get_management_ip(self, host_ip):
        if self.has_host_ip(host_ip):
            return self._host_ip_obj[host_ip].management_ip
        else:
            raise KeyError

    def add_host(self, host):
        """
        :type host: Host
        """
        self._host_ip_obj[host.host_ip] = host

    def remove_host(self, host_ip):
        del self._host_ip_obj[host_ip]
