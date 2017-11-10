#/usr/bin/env python3

from itertools import groupby
from pulp import LpProblem, LpMaximize, LpVariable, LpAffineExpression, value, solvers

def paths_to_nzv(paths):
    p = len(paths)
    pairs = [(c, v) for v in range(p) for c in paths[v]]
    g = groupby(sorted(pairs), lambda e: e[0])
    return { c: list(map(lambda t: t[1], nzv)) for c, nzv in g }

def view_to_constraints(view, xs):
    constraints = []
    for e in view.elements:
        constraints += [e.constraint(xs)]
    return constraints

def view_to_costs(view, n):
    elements = {e.eid: e for e in view.elements}
    paths = view.paths
    return [sum(map(lambda x: elements[x].cost, paths[i])) for i in range(n)]

def nzv2exp(nzv, lpvars):
    """
    lpvars: all LpVariable used in the problem
    constraint: the target constraint
    """
    return LpAffineExpression(map(lambda v: (lpvars[v], 1), nzv))

class Constraint(object):
    """
    Each Constraint represents a linear constraint ax <= b
    """

    def __init__(self, cid, nzv, bound):
        self.cid = cid
        self.nzv = sorted(nzv)
        self.bound = bound
        self.code = sum(map(lambda x: 2 ** x, self.nzv))

    def expr(self, lpvars):
        return nzv2exp(self.nzv, lpvars)

    def __call__(self, lpvars):
        return nzv2exp(self.nzv, lpvars) <= self.bound

    def __repr__(self):
        return "+".join(map(lambda v: "x%s" % v, self.nzv)) + "<=" + str(self.bound)

def construct_prob(n_var, constraints):
    x = {i: LpVariable("x%s"%i, lowBound = 0) for i in range(n_var)}

    prob = LpProblem("MECS", LpMaximize)
    for c in constraints:
        prob += c(x), str(c.cid)
    return x, prob

def is_redundant(constraints, paths, c):
    filtered = [cc for cc in constraints if cc.cid != c.cid]
    xs, prob = construct_prob(len(paths), filtered)
    prob += c.expr(xs)

    prob.solve(solvers.PULP_CBC_CMD(fracGap=10))
    return prob.status == 1 and value(prob.objective) <= c.bound
