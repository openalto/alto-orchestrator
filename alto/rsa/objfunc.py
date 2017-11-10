#!/usr/bin/env python

from itertools import groupby

from pulp import LpProblem, LpAffineExpression, LpMaximize, LpVariable, value
from .lputil import paths_to_nzv, view_to_constraints, view_to_costs

class ObjectiveFunction(object):
    def __init__(self):
        pass

    def solve(self, flowreq, view):
        pass

class WeightedThroughputMaximization(ObjectiveFunction):
    def __init__(self, w):
        self.w = w

    def solve(self, flowreq, view):
        prob = LpProblem("wtm", LpMaximize)
        xs = [LpVariable('x%s'%i, lowBound=0) for i in range(len(self.w))]
        for c in view_to_constraints(view, xs):
            prob += c
        prob += LpAffineExpression(zip(xs, self.w))
        prob.solve()
        return value(prob.objective)

class CoflowCompletionTimeMinimization(ObjectiveFunction):
    def __init__(self, w):
        self.w = w

    def solve(self, flowreq, view):
        nzv = paths_to_nzv(view.paths)
        elements = {e.eid: e for e in view.elements}
        b = min([elements[c].bw / sum([self.w[i] for i in nzv[c]]) for c in nzv])
        return 10**9 / b

class NodeDistanceMinimization(ObjectiveFunction):
    def __init__(self):
        pass

    def solve(self, flowreq, view):
        costs = view_to_costs(view, len(flowreq))
        costs = [(flowreq[i][0], flowreq[i][1], costs[i]) for i in range(len(flowreq))]
        cs = groupby(costs, lambda p: p[0])
        cs = [min(map(lambda p: p[2], s)) for c, s in cs]
        return sum(cs)
