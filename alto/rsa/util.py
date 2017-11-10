#/usr/bin/env python3

from functools import reduce

def argmax(xs, key):
    return reduce(lambda x,y: x if key(x) > key(y) else y, xs)

def rocketfuel_bandwidth_func(g, x, y):
    rocketfuel_bw_table = [100000, 40000, 20000, 10000, 5000, 2000] # Mbps

    node_x, node_y = g.node[x], g.node[y]
    rx, ry = node_x['r'], node_y['r']
    if rx == ry:
        return rocketfuel_bw_table[rx]
    else:
        rmax = int((rx+ry*2)/3)
        return rocketfuel_bw_table[rmax]

def sample(array, cnt):
    import random

    result = []
    while cnt > 0:
        sample_size = min(len(array), cnt)
        result += random.sample(array, sample_size)
        cnt -= sample_size
    return result
