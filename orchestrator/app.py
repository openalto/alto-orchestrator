import falcon
import json
import requests
import zmq
import re

from scipy.optimize import linprog
from orchestrator.data import data


class DATA:
    DEPLOY_URL = ""
    RESOURCE_QUERY_URL = ""
    ON_DEMAND_PCE_URL = ""
    FLOW_ID = 1
    id_map = {}
    sshd_servers = set()
    flow_id_map = {}


DomainData = {}


class RunTaskEntry(object):
    def on_post(self, req, resp):
        lp_results = json.loads(req.stream.read().decode('UTF-8'))

        # Starting SSH server
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:12333")

        for flow_result in lp_results["flows"]:
            flow_id = flow_result["flow-id"]
            bandwidth = flow_result["bandwidth"]
            rate = int(bandwidth / 8.0) + 1
            rate *= 1000

            flow = DATA.flow_id_map[flow_id]
            print(flow)

            src_ip = flow['flow']["src-ip"]
            dst_ip = flow['flow']["dst-ip"]
            src_name = DATA.id_map[src_ip]
            dst_name = DATA.id_map[dst_ip]

            if dst_ip not in DATA.sshd_servers:
                print("Starting SSH Server on %s", dst_ip)
                socket.send_string("%s /usr/sbin/sshd -D &" % dst_name)
                msg = socket.recv()
                print(msg)

                DATA.sshd_servers.add(dst_ip)

            socket.send_string(
                "%s ( dd if=/dev/zero bs=1M count=200000 | pv --rate-limit %d | ssh -oStrictHostKeyChecking=no %s dd of=/dev/null & )" % (
                    src_name, rate, dst_ip
                ))
            msg = socket.recv()
            print(msg)
        socket.close()
        resp.status = falcon.HTTP_200
        resp.body = json.dumps({"result": "OK"})

        DATA.FLOW_ID = 1  # Start from 1 for every submission


class CalculateBandwidthEntry(object):
    def on_post(self, req, resp):
        r = json.loads(req.stream.read().decode('UTF-8'))
        ane_matrix = r["ane-matrix"]
        flow_list = set()
        for row in ane_matrix:
            for item in row:
                flow_list.add(int(item["flow-id"]))
        flow_list = sorted(flow_list)
        var_num = len(flow_list)

        # obj: min cx
        # Constrains: Ax <= b
        c = [-1] * var_num
        A = []
        b = []
        for row, b_value in zip(ane_matrix, r["anes"]):
            A_r = [0] * var_num
            for item in row:
                A_r[flow_list.index(int(item["flow-id"]))] += 1
            A.append(A_r)
            b.append(b_value["availbw"])

        for i in range(var_num):
            A_r = [0] * var_num
            A_r[i] = 1
            A.append(A_r)
            b.append(60000)

        res = linprog(c, A_ub=A, b_ub=b)
        print(res.x)

        results = {"flows": []}
        for i, x in enumerate(res.x):
            flow_id = flow_list[i]
            results["flows"].append({"flow-id": flow_id, "bandwidth": x})
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(results)


def do_path_query(d, resp):
    """
    Input format
    {
      "flows": [
        {
          "src": "10.0.1.100",
          "dst": "10.0.2.100",
          "ingress": "openflow:2:1"
        },
        {
          "src": "10.0.1.101",
          "dst": "10.0.3.100",
          "ingress": "openflow:2:2"
        }
      ]
    }
    """
    flows = d["flows"]
    domain_flows = {}
    r = ""
    for flow in flows:
        src = flow["src"]
        domain_name = data.host_domain_name[src]
        if domain_name not in domain_flows:
            domain_flows[domain_name] = list()
        domain_flows[domain_name].append(flow)
    for domain in domain_flows:
        r = requests.post(
            "http://%s:%d%s" % (data.domain_data[domain]["hostname"], data.path_query_port, data.path_query_uri),
            json={"flows": domain_flows[domain]})
    resp.status = falcon.HTTP_200
    resp.body = r.text
    print(r.text)


def do_resource_query(d, resp):
    print(d)
    full_list = {}
    for domain_name in data.domain_data.keys():
        domain_data = data.domain_data[domain_name]
        url = "http://%s:%d%s" % (domain_data["hostname"], data.resource_query_port, data.resource_query_uri)
        print(url)
        r = requests.post(url, json=d, headers={"content_type": "application/json"})
        full_list[domain_name] = json.loads(r.text)
    resp.status = falcon.HTTP_200
    resp.body = json.dumps(full_list)
    print(full_list)


class TasksEntry(object):
    def on_post(self, req, resp):
        flows = json.loads(req.stream.read().decode("UTF-8"))
        d = {
            "query-desc": []
        }
        DATA.flow_id_map = {}
        DATA.FLOW_ID = 1
        for flow in flows:
            jobs = flow["jobs"]
            for job in jobs:
                src_ip = job["potential_srcs"][0]["ip"]
                dst_ip = job["potential_dsts"][0]["ip"]
                dst_port = job["potential_dsts"][0]["port"]
                d["query-desc"].append({
                    "flow": {
                        "flow-id": DATA.FLOW_ID,
                        "src-ip": src_ip,
                        "dst-ip": dst_ip,
                        "dst-port": dst_port,
                        "protocol": "tcp"
                    }
                })
                DATA.flow_id_map[DATA.FLOW_ID] = {
                    "flow": {
                        "flow-id": DATA.FLOW_ID,
                        "src-ip": src_ip,
                        "dst-ip": dst_ip,
                        "dst-port": dst_port,
                        "protocol": "tcp"
                    }
                }
                DATA.FLOW_ID += 1
        do_resource_query(d, resp)


class PathQueryEntry(object):
    def on_post(self, req, resp):
        do_path_query(json.loads(req.stream.read().decode("UTF-8")), resp)


class ResourceQueryEntry(object):
    def on_post(self, req, resp):
        d = json.loads(req.stream.read().decode("UTF-8"))
        do_resource_query(d, resp)


class OnDemandPCEEntry(object):
    def on_post(self, req, resp):
        flows = json.loads(req.stream.read().decode("UTF-8"))
        d = []
        for flow in flows:
            jobs = flow["jobs"]
            for job in jobs:
                src_ip = job["potential_srcs"][0]["ip"]
                dst_ip = job["potential_dsts"][0]["ip"]
                item = {
                    "src": src_ip,
                    "dst": dst_ip,
                }
                item.update(job.get("demand", {}))
                d.append(item)

        print(DATA.ON_DEMAND_PCE_URL)
        print(d)
        r = requests.post(DATA.ON_DEMAND_PCE_URL, json=d, headers={"content_type": "application/json"})
        resp.status = falcon.HTTP_200
        resp.body = r.text
        print(r.text)


class RegisterEntry(object):
    def on_post(self, req, resp):
        raw_data = req.stream.read()
        info = json.loads(raw_data.decode('utf-8'))
        hostname = re.search("(?<=^http://)\w+(?=\:)", info["deploy-url"]).group(0)
        data.domain_data[info["domain-name"]]["hostname"] = hostname
        DATA.DEPLOY_URL = info["deploy-url"]
        DomainData[info["domain-name"]] = info
        print(info)

        resp.status = falcon.HTTP_200
        resp.body = """ {"code": "OK"} """


class StopTaskEntry(object):
    def on_post(self, req, resp):
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:12333")
        host_name = list(DATA.id_map.values())[0]  # Choose a host name randomly
        socket.send_string("siteA_s1 pkill dd")
        socket.recv()
        socket.close()
        resp.status = falcon.HTTP_200
        resp.status = """{"code": "OK"}"""


class RunTaskInterdomainEntry(object):
    def on_post(self, req, resp):
        lp_results = json.loads(req.stream.read().decode('UTF-8'))
        interdomain_flow_id_map = {
            1: {
                "src-ip": "10.0.1.101",
                "dst-ip": "10.0.2.201"
            },
            2: {
                "src-ip": "10.0.1.102",
                "dst-ip": "10.0.2.202"
            }
        }

        interdomain_id_map = {
            "10.0.1.101": "siteA_s1",
            "10.0.1.102": "siteA_s2",
            "10.0.2.201": "siteC_d1",
            "10.0.2.202": "siteC_d2",
        }

        # Starting SSH server
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:12333")

        for name, dst in [("siteC_d1", "10.0.2.201"), ("siteC_d2", "10.0.2.202")]:
            if dst not in DATA.sshd_servers:
                print("Starting SSH Server on %s", dst)
                socket.send_string("%s /usr/sbin/sshd -D &" % name)
                msg = socket.recv()
                print(msg)

                DATA.sshd_servers.add(dst)

        socket.send_string(
            "siteA_s1 ( dd if=/dev/zero bs=1M count=200000 | pv --rate-limit 5000k | ssh -oStrictHostKeyChecking=no 10.0.2.201 dd of=/dev/null & )")
        socket.recv()
        socket.send_string(
            "siteA_s2 ( dd if=/dev/zero bs=1M count=200000 | pv --rate-limit 5000k | ssh -oStrictHostKeyChecking=no 10.0.2.202 dd of=/dev/null & )")
        socket.recv()
        socket.close()
        #
        # for flow_result in lp_results["flows"]:
        #     flow_id = flow_result["flow-id"]
        #     bandwidth = flow_result["bandwidth"]
        #     rate = int(bandwidth / 8.0) + 1
        #     rate *= 1000
        #
        #     flow = interdomain_flow_id_map[flow_id]
        #     print(flow)
        #
        #     src_ip = flow["src-ip"]
        #     dst_ip = flow["dst-ip"]
        #     src_name = interdomain_id_map[src_ip]
        #     dst_name = interdomain_id_map[dst_ip]
        #
        #     if dst_ip not in DATA.sshd_servers:
        #         print("Starting SSH Server on %s", dst_ip)
        #         socket.send_string("%s /usr/sbin/sshd -D &" % dst_name)
        #         msg = socket.recv()
        #         print(msg)
        #
        #         DATA.sshd_servers.add(dst_ip)
        #
        #     socket.send_string(
        #         "%s ( dd if=/dev/zero bs=1M count=200000 | pv --rate-limit %d | ssh -oStrictHostKeyChecking=no %s dd of=/dev/null & )" % (
        #             src_name, rate, dst_ip
        #         ))
        #     msg = socket.recv()
        #     print(msg)
        # socket.close()
        resp.status = falcon.HTTP_200
        resp.body = json.dumps({"result": "OK"})


app = falcon.API()

app.add_route('/tasks', TasksEntry())
app.add_route('/register', RegisterEntry())
app.add_route('/calculate_bandwidth', CalculateBandwidthEntry())
app.add_route('/run_task', RunTaskEntry())
app.add_route('/run_task_interdomain', RunTaskInterdomainEntry())
app.add_route('/resource_query', ResourceQueryEntry())
app.add_route('/on_demand_pce', OnDemandPCEEntry())
app.add_route('/stop_task', StopTaskEntry())
app.add_route('/path-query', PathQueryEntry())

DATA.id_map = json.load(open('name-map.json'))
