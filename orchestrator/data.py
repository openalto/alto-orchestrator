import os
import json


class Data(object):
    def __init__(self, config_file=None):
        if config_file is None:
            config_file = os.environ["HOME"] + "/sc18.json"

        self.domain_data = {}

        self.path_query_port = 8399
        self.path_query_uri = "/path-query"
        self.resource_query_port = 8080
        self.resource_query_uri = "/experimental/v1/unicorn/resource-query"

        self.host_domain_name = {}
        self._read_config_file(config_file)

    def _read_config_file(self, config_file):
        self.domain_data = json.load(open(config_file))
        for domain_name in self.domain_data:
            hosts = self.domain_data[domain_name]["hosts"]
            for host in hosts:
                self.host_domain_name[host] = domain_name


data = Data(config_file='/home/ubuntu/sc18.json')
