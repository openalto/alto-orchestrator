#!/usr/bin/env python

from functools import reduce, partial
from pulp import value
from .lputil import paths_to_nzv, Constraint, construct_prob, is_redundant
from .view import Element, View
from .mecs import EquivAggregation, EquivDecomposition

class Abstraction(object):
    def __init__(self, g, paths):
        self.g = g
        paths = list(map(lambda p: list(zip(p[:-1], p[1:])), paths))

        pairs = list(reduce(lambda x, y: set(x) | set(y), paths))
        self.eid = {pairs[i]: i for i in range(len(pairs))}
        paths = [list(map(lambda p: self.eid[p], paths[i])) for i in range(len(paths))]
        nzv = paths_to_nzv(paths)
        bws = {self.eid[(u, v)]: g[u][v]['capacity'] for u, v in pairs}
        costs = {self.eid[(u, v)]: g[u][v]['routingcost'] for u, v in pairs}

        elefunc = lambda eid: Element(eid, nzv[eid], bws[eid], costs[eid])
        elements = [elefunc(self.eid[i]) for i in self.eid]
        self.view = View(paths, elements)

    def get_view(self, with_bw=True, with_rc=True):
        pass

class RawNetworkView(Abstraction):
    def __init__(self, g, paths):
        Abstraction.__init__(self, g, paths)

    def get_view(self, with_bw=True, with_rc=True):
        return self.view

class MecsNetworkView(Abstraction):
    def __init__(self, g, paths):
        Abstraction.__init__(self, g, paths)

    def get_view(self, with_bw=True, with_rc=True):
        transform = EquivAggregation()
        self.view = transform(self.view)
        decomposable = set()
        if with_bw:
            from multiprocessing import Pool

            constraints = list(map(lambda e: e.constraint, self.view.elements))
            with Pool(8) as p:
                results = p.map(partial(is_redundant, constraints, self.view.paths), constraints, 64)

            decomposable = {constraints[i].cid for i in range(len(constraints)) if results[i]}
        else:
            decomposable = set(map(lambda e: e.eid, self.view.elements))
        if not with_rc:
            return self.view.shrink(decomposable)
        else:
            for i in range(3):
                transform = EquivDecomposition()
                self.view = transform(self.view, decomposable)
            return transform(self.view, decomposable)

class ObsNetworkView(Abstraction):
    def __init__(self, g, paths):
        Abstraction.__init__(self, g, paths)

    def get_view(self, with_bw=True, with_rc=True):
        paths = self.view.paths
        edge = reduce(lambda x, y: x|y, map(lambda p: {p[0], p[-1]}, paths))
        non_edge = [k.eid for k in self.view.elements if k.eid not in edge]
        return self.view.shrink(non_edge)

class End2EndNetworkView(Abstraction):
    def __init__(self, g, paths):
        Abstraction.__init__(self, g, paths)

    def get_view(self, with_bw=False, with_rc=True):
        paths = self.view.paths
        elements = self.view.elements
        costs = [sum(map(lambda k: elements[k].cost, p)) for p in paths]
        bws = [min(map(lambda k: elements[k].bw, p)) for p in paths]
        elements = [Element(i, [i], bws[i], costs[i]) for i in range(len(paths))]
        paths = [[i] for i in range(len(paths))]
        return View(paths, elements)
