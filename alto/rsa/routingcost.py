#!/usr/bin/env python

def augment_topology(g):
    import random

    ng = g.copy()

    total_bw = sum([ng[u][v]['capacity'] for u, v in ng.edges()])
    ave_bw = total_bw / len(ng.edges())
    for u, v in ng.edges():
        multiplier = abs(random.gauss(1, 1) + 1e-2) * ave_bw
        ng[u][v]['routingcost'] = multiplier / ng[u][v]['capacity']
    return ng

def save_routing_metric(g, filename):
    with open(filename, 'w') as f:
        for u, v in g.edges():
            print(u, v, g[u][v]['routingcost'], file=f)

def load_routing_metric(g, filename):
    with open(filename, 'r') as f:
        for l in f.readlines():
            u, v, c = l.split(' ')
            g[u][v]['routingcost'] = float(c)
