import falcon
import json
import requests

AGENT_ADDRESS = "http://127.0.0.1:6789"
RESOURCE_QUERY_ROUTE = "/resource-query"


class ResourceQueryEntry(object):
    def on_post(self, req, resp):
        flows = json.loads(req.stream.read().decode("UTF-8"))
        flow_id = 1
        d = {
            "query_desc": []
        }
        for flow in flows:
            id = flow["id"]
            jobs = flow["jobs"]
            for job in jobs:
                src_ip = job["potential_srcs"][0]["ip"]
                dst_ip = job["potential_dsts"][0]["ip"]
                dst_port = job["potential_dsts"][0]["port"]
                d["query_desc"].append({
                    "flow-id": flow_id,
                    "src-ip": src_ip,
                    "dst-ip": dst_ip,
                    "dst-port": dst_port,
                    "protocol": "tcp"
                })
                flow_id += 1
        r = requests.post(AGENT_ADDRESS + RESOURCE_QUERY_ROUTE, json=d, headers={"content_type": "application/json"})
        print(r.text)
        # TODO: get agent response
        resp.status = falcon.HTTP_200
        resp.body = """ {"code": "OK"} """


app = falcon.API()

app.add_route('/resource-query', ResourceQueryEntry())
