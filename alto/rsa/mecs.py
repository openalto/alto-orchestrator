#!/usr/bin/env python

from itertools import groupby
from pulp import LpAffineExpression, LpVariable, LpProblem, LpMaximize
from view import Element, View

class EquivTransformation(object):
    def __init__(self):
        pass

    def __call__(self):
        pass

class EquivAggregation(EquivTransformation):
    def __init__(self):
        EquivTransformation.__init__(self)

    def __call__(self, view):
        paths = view.paths
        elements = view.elements
        elements = sorted(elements, key=lambda e: e.code)
        g = groupby(elements, lambda e: e.code)

        nelements = []
        aggregated = []

        for k, v in g:
            v = list(v)
            eid = v[0].eid
            nzv = v[0].nzv
            aggregated += list(map(lambda e: e.eid, v[1:]))
            bw = min(map(lambda e: e.bw, v))
            # cost = sum(map(lambda e: e.cost, v))
            # nelements += [Element(eid, nzv, bw, cost)]
            nelements += [Element(eid, nzv, bw)]

        view = View(paths, nelements)
        return view.shrink(aggregated)

class EquivDecomposition(EquivTransformation):
    def __init__(self):
        EquivTransformation.__init__(self)

    def __call__(self, view, decomposable):
        elements = sorted(view.elements, key=lambda e: e.code, reverse=True)
        removed = []
        for e in elements:
            if not e.eid in decomposable:
                continue
            code = e.code
            for ej in elements:
                if code == 0:
                    break
                if ej.eid == e.eid:
                    continue
                if ej.code & code == ej.code:
                    ej.bw = min(ej.bw, e.bw)
                    ej.cost += e.cost
                    e.nzv = list(set(e.nzv) - set(ej.nzv))
                    code = code ^ ej.code
                    assert code == sum(map(lambda x: 2 ** x, e.nzv))

            e.code = code
            if code == 0:
                removed += [e.eid]
        pairs = sorted([(p, e.eid) for e in elements for p in e.nzv])
        paths = []
        for k, v in groupby(pairs, key=lambda x: x[0]):
            paths += [list(map(lambda p: p[1], v))]
        view = View(paths, elements)
        return view.shrink(removed)
