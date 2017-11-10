#!/usr/bin/env python3

from functools import reduce
import sys
import re
import fnss
from networkx import connected_components, all_pairs_shortest_path, DiGraph
from networkx import read_graphml, write_graphml

from .util import argmax, rocketfuel_bandwidth_func

class Topology(object):

    def __init__(self, g):
        self.g = g

    def apply(self):
        pass

    def select_largest_cc(self):
        g = self.g
        mscc = argmax(connected_components(g), len)
        to_be_removed = set(g.nodes()) - set(mscc)
        g.remove_nodes_from(to_be_removed)

    def unify_graph_attr(self, bw_func, excluded_func):
        g = self.g
        for nid in g.nodes():
            n = g.node[nid]
            g.node[nid]['excluded'] = excluded_func(n)

        for x, y in g.edges():
            g.edge[x][y]['capacity'] = bw_func(g, x, y)
            g.edge[x][y]['load'] = 0
        g.graph['capacity_unit'] = "bps"

class ZooTopology(Topology):
    def __init__(self, filename):
        g = fnss.parse_topology_zoo(filename).to_undirected()
        Topology.__init__(self, g)

    def apply(self):
        self.select_largest_cc()
        self.ensure_internal_info()
        self.ensure_bandwidth_info()

        excluded_func = lambda n: n['type'] == 'internal'
        bw_func = lambda g, x, y: g.edge[x][y]['bandwidth']

        self.unify_graph_attr(bw_func, excluded_func)
        return self.g

    def ensure_internal_info(self):
        g = self.g
        has_internal = reduce(lambda x,y: x or 'Internal' in g.node[y], g.nodes(), False)
        if not has_internal:
            apsp = all_pairs_shortest_path(g)
            dmax = {n: max(map(lambda p: len(apsp[n][p]), apsp[n])) for n in g.nodes()}
            dall = [dmax[n] for n in g.nodes()]
            dave = sum(dall) / len(dall)
            for n in g.nodes():
                g.node[n]['Internal'] = True if dmax[n] < dave else False

        for n in g.nodes():
            g.node[n]['type'] = 'internal' if g.node[n]['Internal'] else 'external'

    def ensure_bandwidth_info(self):
        g = self.g

        bw_table = [100, 40, 10]
        total = [0, 0, 0]
        cnt = [0, 0, 0]
        for (u, v) in g.edges():
            type = (g.node[u]['type'] != 'internal') + (g.node[v]['type'] != 'internal')
            g[u][v]['type'] = type
            if 'label' not in g.edge[u][v]:
                g[u][v]['label'] = str(bw_table[type]) + " Mbps"
            label = g[u][v]['label']
            m = re.search('([0-9]+) ([GMK])b', label)
            if m is None:
                continue
            unit = 10**9 if 'G' == m.group(2) else 10**6 if 'M' else 10**3
            bw = int(m.group(1)) * unit
            g[u][v]['bandwidth'] = bw
            total[type] += bw
            cnt[type] += 1

        if reduce(lambda x,y: x or y == 0, cnt, False):
            ave = bw_table
        else:
            ave = [total[i] / cnt[i] for i in range(3)]
        for u, v in g.edges():
            if 'bandwidth' not in g[u][v]:
                g[u][v]['bandwidth'] = ave[g[u][v]['type']]

class RocketfuelTopology(Topology):
    def __init__(self, filename):
        g = fnss.parse_rocketfuel_isp_map(filename).to_undirected()
        Topology.__init__(self, g)

    def apply(self):
        self.select_largest_cc()

        excluded_func = lambda n: n['type'] == 'internal'
        bw_func = rocketfuel_bandwidth_func

        self.unify_graph_attr(bw_func, excluded_func)
        return self.g

def load_topology(filename, topology_type='rocketfuel'):
    if 'topologyzoo' == topology_type:
        topology = ZooTopology(filename)
    elif 'rocketfuel':
        topology = RocketfuelTopology(filename)
    else:
        topology = None
        print("Unsupported file format!")
        sys.exit(-1)
    return topology.apply()

def dump_topology(g, outfile):
    print(len(g.nodes()), file=outfile)
    print(len(g.edges()), file=outfile)
    candidates = list(filter(lambda n: g.node[n]['excluded'] == False, g.nodes()))
    print(len(candidates), file=outfile)
    print(' '.join(map(str, candidates)), file=outfile)

    for (u, v) in g.edges():
        print(u, v, g.edge[u][v]['capacity'], file=outfile)

def dump_raw_topology(g, filename):
    ng = DiGraph()
    for (u, v) in g.edges():
        ng.add_edge(u, v, capacity=g.edge[u][v]['capacity'])
        ng.add_edge(v, u, capacity=g.edge[u][v]['capacity'])

    for u in g.nodes():
        ng.node[u]['excluded'] = g.node[u]['excluded']

    write_graphml(ng, filename)

def load_raw_topology(filename):
    return read_graphml(filename)

def process_topology(filename):
    ext = filename.split('.')[-1]
    topo_type = 'rocketfuel' if ext == 'cch' else 'topologyzoo'
    g = load_topology(filename, topo_type)
    return g

if __name__ == "__main__":
    filename = sys.argv[1]

    print("Loading topology...", file=sys.stderr)
    process_topology(filename)
    print("Loading topology...Done", file=sys.stderr)
    dump_topology(g, outfile)
