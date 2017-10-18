import json
import urllib.parse
import urllib.request
from threading import Thread

from .data_provider import PathQueryData, DomainsData


class PathQueryThread(Thread):
    def __init__(self, domain_name, flows):
        super().__init__(domain_name, flows)
        self.domain_name = domain_name
        self.flows = flows

    def run(self):
        url = DomainsData().domains[self.domain_name]["controller-url"]
        data = []

        # flow is a 5-tuple: (src-ip, src-port, dst-ip, dst-port, protocol)
        for flow in self.flows:
            data.append({
                "ingress-point": PathQueryData.getLastHop(flow),
                "flow": {
                    "src-ip": flow[0],
                    "src-port": flow[1],
                    "dst-ip": flow[2],
                    "dst-port": flow[3],
                    "protocol": flow[4]
                }
            })

        # send query to domains
        query_data = urllib.parse.urlencode(data)
        req = urllib.request.Request(url, query_data)
        req.add_header("Content-Type", "application/json")
        response = urllib.request.urlopen(req)
        response_data = response.read()
        next_hops = json.loads(response_data)

        # Write result to PathQueryData
        path_data = list(zip(self.flows, next_hops))
        for flow_next_hop in path_data:
            PathQueryData().addPath(flow_next_hop[0], flow_next_hop[1])
