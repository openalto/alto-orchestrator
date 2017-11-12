#!/usr/bin/env python3

import json
from abstraction import MecsNetworkView

def resource_query_transform(response):
    response
    bws = [ane['availbw'] for ane in response['anes']]
    paths_map = dict()
    ane_matrix = response['ane-matrix']
    for i in range(len(ane_matrix)):
        for flow in ane_matrix[i]:
            if flow.get('coefficient', 1) == 0:
                continue
            flow_id = flow['flow-id']
            path = paths_map.get(flow_id, [])
            path.append(i)
            paths_map[flow_id] = path
    flow_ids = list(paths_map.keys())
    paths = [paths_map[fid] for fid in flow_ids]
    mecs = MecsNetworkView(paths, bws)
    view = mecs.get_view()
    new_anes = [{"availbw": e.bw} for e in view.elements]
    new_ane_matrix = [[{"flow-id": flow_ids[i]} for i in e.nzv] for e in view.elements]
    return {"anes": new_anes, "ane-matrix": new_ane_matrix}

if '__main__' == __name__:
    test_data = {
        "anes": [{"availbw": 3}, {"availbw": 7}, {"availbw": 3}],
        "ane-matrix": [
            [{"flow-id": "0"}, {"flow-id": "1"}],
            [{"flow-id": "1"}, {"flow-id": "2"}],
            [{"flow-id":"2"}]
        ]
    }
    print("original:", test_data)
    print("rsa:", resource_query_transform(test_data))