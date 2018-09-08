import falcon
import json
import requests
import scipy
import zmq

from scipy.optimize import linprog


class DATA:
    DEPLOY_URL = ""
    RESOURCE_QUERY_URL = ""
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
                "%s ( dd if=/dev/zero bs=1M count=200 | pv --rate-limit %dk | ssh -oStrictHostKeyChecking=no %s dd of=/dev/null & )" % (
                    src_name, rate, dst_ip
                ))
            msg = socket.recv()
            print(msg)
        socket.close()
        resp.status = falcon.HTTP_200
        resp.body = json.dumps({"result": "OK"})


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


class TasksEntry(object):
    def on_post(self, req, resp):
        flows = json.loads(req.stream.read().decode("UTF-8"))
        d = {
            "query-desc": []
        }
        DATA.flow_id_map = {}
        for flow in flows:
            id = flow["id"]
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
        print(DATA.RESOURCE_QUERY_URL)
        print(d)
        r = requests.post(DATA.RESOURCE_QUERY_URL, json=d, headers={"content_type": "application/json"})
        resp.status = falcon.HTTP_200
        resp.body = r.text
        print(r.text)


class RegisterEntry(object):
    def on_post(self, req, resp):
        raw_data = req.stream.read()
        info = json.loads(raw_data.decode('utf-8'))
        DATA.DEPLOY_URL = info["deploy-url"]
        DATA.RESOURCE_QUERY_URL = DATA.DEPLOY_URL.replace("deploys", "resource-query")
        DomainData[info["domain-name"]] = info
        print(info)

        resp.status = falcon.HTTP_200
        resp.body = """ {"code": "OK"} """


app = falcon.API()

app.add_route('/tasks', TasksEntry())
app.add_route('/register', RegisterEntry())
app.add_route('/calculate_bandwidth', CalculateBandwidthEntry())
app.add_route('/run_task', RunTaskEntry())

DATA.id_map = json.load(open('name-map.json'))
