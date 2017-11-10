#!/usr/bin/env python

from .lputil import paths_to_nzv, Constraint, construct_prob

class Element(object):
    def __init__(self, eid, nzv, bw, cost):
        self.eid = eid
        self.nzv = nzv
        self.bw = bw
        self.cost = cost
        self.constraint = Constraint(eid, nzv, bw)
        self.code = sum(map(lambda x: 2 ** x, self.nzv))

class View(object):
    def __init__(self, paths, elements):
        self.paths = paths
        self.elements = elements

    def shrink(self, removed):
        removed = set(removed)
        paths = list(map(lambda p: set(p) - removed, self.paths))
        elements = list(filter(lambda e: e.eid not in removed, self.elements))

        return View(paths, elements)
