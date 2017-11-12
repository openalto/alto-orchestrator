#!/usr/bin/env python

from functools import partial
from lputil import paths_to_nzv, is_redundant
from view import Element, View
from mecs import EquivAggregation, EquivDecomposition

class Abstraction(object):
    def __init__(self, paths, bws):
        nzv = paths_to_nzv(paths)
        elefunc = lambda eid: Element(eid, nzv[eid], bws[eid])
        eid = range(len(bws))
        elements = [elefunc(eid[i]) for i in eid]
        self.view = View(paths, elements)

    def get_view(self, with_bw=True, with_rc=True):
        pass

class MecsNetworkView(Abstraction):
    def __init__(self, paths, bws):
        Abstraction.__init__(self, paths, bws)

    def get_view(self):
        transform = EquivAggregation()
        self.view = transform(self.view)
        decomposable = set()
        from multiprocessing import Pool

        constraints = list(map(lambda e: e.constraint, self.view.elements))
        with Pool(8) as p:
            results = p.map(partial(is_redundant, constraints, self.view.paths), constraints, 64)

        decomposable = {constraints[i].cid for i in range(len(constraints)) if results[i]}
        return self.view.shrink(decomposable)

if '__main__' == __name__:
    paths = [[0], [0, 1], [1, 2]]
    bws = {0: 3, 1: 7, 2: 3}
    mecs = MecsNetworkView(paths, bws)
    view = mecs.get_view()
    print(view.paths)
    print(view.elements)