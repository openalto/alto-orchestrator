#!/usr/bin/env python

import random
from .topology import process_topology
from .routingcost import augment_topology
from .flowrequest import gen_flowreq
from .routingmatrix import get_rmatrix
from .abstraction import RawNetworkView, MecsNetworkView
from .abstraction import ObsNetworkView, End2EndNetworkView
from .objfunc import WeightedThroughputMaximization
from .objfunc import CoflowCompletionTimeMinimization
from .objfunc import NodeDistanceMinimization

if __name__ == '__main__':
    import sys, time

    filename = sys.argv[1]
    n, m = int(sys.argv[2]), int(sys.argv[3])
    g = process_topology(filename)
    g = augment_topology(g)
    fr = gen_flowreq(g, 'ftm', n, m)
    rmatrix = get_rmatrix(g, fr)

    w = [random.random() for i in range(n * m)]
    objs = [WeightedThroughputMaximization(w),
            CoflowCompletionTimeMinimization(w),
            NodeDistanceMinimization()]

    results = []
    config = [(RawNetworkView, True, True),
              (MecsNetworkView, True, False),
              (MecsNetworkView, False, True),
              (MecsNetworkView, True, True),
              (ObsNetworkView, True, False),
              (End2EndNetworkView, False, True)]
    for c in config:
        anv, with_bw, with_rc = c
        gs = g.copy()
        rs = rmatrix.copy()
        nv = anv(gs, rs)
        start = time.clock()
        view = nv.get_view(with_bw=with_bw, with_rc=with_rc)
        end = time.clock()

        results += [len(view.elements)]
        for obj in objs:
            opt = obj.solve(fr, view)
            results += [opt]

    print(' '.join(map(str, results)))
