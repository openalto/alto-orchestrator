#!/usr/bin/env python

from pulp import *

class SimpleScheduler:
    """
    A simple implementation of unicorn orchestrator scheduler.
    """

    def __init__(self):
        self.bijkName2bijkVar = {}
        self.rsaCs = []
        self.jobId2DataSize = {}
        self.bsmall = LpVariable("bsmall", 0)
        self.jobId2Num = {}
        self.jobId2Flows = {}

        self.prob = LpProblem("cms-problem", LpMaximize)
        self.prob += self.bsmall

    def setRSAConstraints(self):
        for rsaC in self.rsaCs:
            bijkL = []
            flows = str(rsaC).split(" ")[:-1]
            bw = int(str(rsaC).split(" ")[-1])
            for bijkStr in flows:
                bijk = None
                if bijkStr not in self.bijkName2bijkVar:
                    bijk = LpVariable(bijkStr, 0)
                    self.bijkName2bijkVar[bijkStr] = bijk
                else:
                    bijk = self.bijkName2bijkVar[bijkStr]
                bijkL.append(bijk)
            self.prob += lpSum(bijkL) <= bw

    def setGlobalVars(self, filename):
        flow2JobId = {}
        with open(filename) as f:
            for line in f:
                if str(line).__contains__("B"):
                    self.rsaCs.append(line)
                    flows = str(line).split(" ")[:-1]
                    for flow in flows:
                        flow2JobId[flow] = str(flow).split("_")[1]
                else:
                    jobId2DataSizeStr = str(line).split(" ")
                    for j2d in jobId2DataSizeStr:
                        jobId = str(j2d).split("=")[0]
                        dataSize = str(j2d).split("=")[1]
                        self.jobId2DataSize[jobId] = dataSize
        for flow in flow2JobId:
            jobId = str(flow).split("_")[1]
            if jobId not in self.jobId2Num:
                self.jobId2Num[jobId] = 1
            else:
                self.jobId2Num[jobId] += 1
            if jobId not in self.jobId2Flows:
                self.jobId2Flows[jobId] = [flow]
            else:
                self.jobId2Flows[jobId].append(flow)

    def setBijkAndBsmall(self):
        for jobId in self.jobId2DataSize:
            Bi = int(self.jobId2DataSize[jobId]) * self.bsmall
            # self.prob += lpSum(self.bijkName2bijkVar[bijkName] for bijkName in self.jobId2Flows[jobId]) - Bi * self.jobId2Num[jobId] == 0
            self.prob += lpSum(self.bijkName2bijkVar[bijkName] for bijkName in self.jobId2Flows[jobId]) - Bi == 0

    def report(self):
        print(LpStatus[self.prob.status])

        for v in self.prob.variables():
            print(v.name, "=", v.varValue)

    def info(self):
        print(self.bijkName2bijkVar)
        print(self.jobId2DataSize)
        print(self.jobId2Num)
        print(self.jobId2Flows)

    def solve(self):
        self.prob.solve()

if __name__ == '__main__':
    sched = SimpleScheduler()

    sched.setGlobalVars("file1")
    sched.setRSAConstraints()
    sched.setBijkAndBsmall()

    sched.info()

    sched.solve()

    sched.report()
