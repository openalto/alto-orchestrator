#!/usr/bin/env python

from networkx import shortest_path

def get_rmatrix(g, flowreq):
    nodes = {u for u, v in flowreq}
    paths = {c: shortest_path(g, source=c, weight='routingcost') for c in nodes}

    return [paths[u][v] for u, v in flowreq]

def save_rmatrix(rmat, filename):
    with open(filename, 'w') as f:
        for row in rmat:
            print(' '.join(map(str, row)), file=f)

def load_rmatrix(filename):
    rmat = []
    with open(filename, 'r') as f:
        for l in f.readlines():
            rmat += [list(map(str.strip, l.split(' ')))]
    return rmat
