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

    def ip2DomainName(self, ip):
        return self.ip2domain[ip]


class PathQueryData(metaclass=SingletonType):
    def __init__(self):
        super(PathQueryData, self).__init__()

        # flow -> path
        self.flowsPath = dict()

        # lock
        self.lock = False

        self.reachedFlow = set()

    def clear(self):
        self.flowsPath = dict()
        self.lock = False
        self.reachedFlow.clear()

    def addhop(self, flow, hop):
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

    def addReachedFlow(self, flow):
        self.reachedFlow.add(flow)

    def isFlowReached(self, flow):
        return flow in self.reachedFlow

class ResourceQueryData(metaclass=SingletonType):
    def __init__(self):
        super(ResourceQueryData, self).__init__()
        self.domains_abstraction = dict()

    def addAbstraction(self, domain, abstraction):
        self.domains_abstraction[domain] = abstraction

    def __iter__(self):
        for domain in self.domains_abstraction.keys():
            yield domain

    def __contains__(self, item):
        return item in self.domains_abstraction

    def __getitem__(self, item):
        return self.domains_abstraction[item]
