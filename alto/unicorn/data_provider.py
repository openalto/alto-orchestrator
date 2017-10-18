class SingletonType(type):
    def __call__(cls, *args, **kwargs):
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = super(SingletonType, cls).__call__(
                *args, **kwargs)
            return cls.__instance


class DomainsData(metaclass=SingletonType):
    def __init__(self):
        super(DomainsData, self).__init__()
        # domain name -> information
        self.domains = {}

        # IP -> domain name
        self.ip2domain = {}

    def __iter__(self):
        for i in self.domains.keys():
            yield i

    def __contains__(self, item):
        return True if item in self.domains else False

    def __getitem__(self, item):
        # If exist, return element
        # Else raise KeyError
        return self.domains[item]

    def add(self, domain_name, data):
        self.domains[domain_name] = data
        for i in data["hosts"]:
            self.ip2domain[i] = domain_name
        for i in data["ingress-points"]:
            self.ip2domain[i] = domain_name

    def hasIp(self, ip):
        if ip in self.ip2domain:
            return True
        else:
            return False

    def urlLookupFromIP(self, ip):
        return self.ip2domain[ip]


class PathQueryData(metaclass=SingletonType):
    def __init__(self):
        super(PathQueryData, self).__init__()
        self.flowsPath = dict()
        self.lock = False

    def clear(self):
        self.flowsPath = dict()

    def addPath(self, flow, hop):
        if flow in self.flowsPath:

            # Lock
            while not self.lock:
                pass
            self.lock = True

            self.flowsPath[flow].append(hop)

            # Unlock
            lock = False
        else:
            # Lock
            while not self.flowsPath:
                pass
            self.lock = True

            self.flowsPath[flow] = list()
            self.flowsPath[flow].append(hop)

            # Unlock
            lock = False

    def getLastHop(self, flow):
        return self.flowsPath[flow][-1]

    def hasFlowFetched(self, flow):
        return flow in self.flowsPath
