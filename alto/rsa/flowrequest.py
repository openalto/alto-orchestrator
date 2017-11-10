#!/usr/bin/env python

from .topology import process_topology
from .util import sample

class FlowRequestGenerator(object):
    def __init__(self, n, m):
        self.n, self.m = int(n), int(m)

    def generate(self, g):
        pass

class FewToManyGenerator(FlowRequestGenerator):
    def __init__(self, n, m):
        FlowRequestGenerator.__init__(self, n, m)

    def generate(self, g):
        n, m = self.n, self.m
        candidates = list(filter(lambda n: not g.node[n]['excluded'], g.nodes()))

        lhs = sample(candidates, n)
        candidates = [n for n in candidates if n not in lhs]
        if len(candidates) == 0:
            raise Exception("Not enough candidate nodes")
        rhs = sample(candidates, m)

        return [(x, y) for x in lhs for y in rhs]

class FewToRandomGenerator(FlowRequestGenerator):
    def __init__(self, n, m):
        FlowRequestGenerator.__init__(self, n, m)

    def genereate(self, g):
        n, m = self.n, self.m
        candidates = list(filter(lambda n: not g.node[n]['excluded'], g.nodes()))

        lhs = sample(candidates, n)
        candidates = [n for n in candidates if n not in lhs]
        if len(candidates) == 0:
            raise Exception("Not enough candidate nodes")
        rhs = [n for n in candidates]

        return [(x, y) for x in lhs for y in sample(rhs, m)]

class ManyToManyGenerator(FlowRequestGenerator):
    def __init__(self, n, m):
        FlowRequestGenerator.__init__(self, n, m)

    def generate(self, g):
        n, m = self.n, self.m
        candidates = list(filter(lambda n: not g.node[n]['excluded'], g.nodes()))

        lhs = sample(candidates, n)

        return [(x, y) for x in lhs for y in sample([z for z in lhs if z != x], m)]

def gen_flowreq(g, pattern, *args):
    if 'ftm' == pattern:
        gen = FewToManyGenerator(*args)
    elif 'mtm':
        gen = ManyToManyGenerator(*args)
    else:
        gen = FewToRandomGenerator(*args)
    return gen.generate(g)

def save_flowreq(fr, filename):
    with open(filename, 'w') as f:
        for x, y in fr:
            print(x, y, file=f)

def load_flowreq(filename):
    fr = []
    with open(filename, 'r') as f:
        for l in f.readlines():
            x, y = l.split(' ')
            fr += [(x.strip(), y.strip())]
    return fr

if __name__ == '__main__':
    import sys

    g = process_topology(sys.argv[1])
    print(gen_flowreq(g, sys.argv[2], *sys.argv[3:]))
