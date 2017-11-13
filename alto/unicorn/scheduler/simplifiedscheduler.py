from pulp import *
from alto.unicorn.scheduler.schedulerdataformat import *


class SimplifiedScheduler:

    def __init__(self):
        self.bijkName2bijkVar = {}

        self.rsaCs = []

        self.jobId2DataSize = {}

        self.bsmall = LpVariable("bsmall", 0)

        self.jobId2Num = {}

        self.jobId2Flows = {}






    def setRSAConstraints(self, prob):
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
            prob += lpSum(bijkL) <= bw


    def setGlobalVarsFromDataStruc(self, rsaDataSize):
        flow2JobId = {}
        for line in rsaDataSize.getLines():
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

    def setBijkAndBsmall(self, prob):
        for jobId in self.jobId2DataSize:
            Bi = int(self.jobId2DataSize[jobId]) * self.bsmall
            #prob += lpSum(bijkName2bijkVar[bijkName] for bijkName in jobId2Flows[jobId]) - Bi * jobId2Num[jobId] == 0
            prob += lpSum(self.bijkName2bijkVar[bijkName] for bijkName in self.jobId2Flows[jobId]) - Bi == 0


    def getFirstRunResult(self, rsaDataSize):
        result = FirstRunResult()
        prob = LpProblem("cms-problem", LpMaximize)

        prob += self.bsmall

        self.setGlobalVarsFromDataStruc(rsaDataSize)
        self.setRSAConstraints(prob)
        self.setBijkAndBsmall(prob)

        print(self.bijkName2bijkVar)
        print(self.jobId2DataSize)
        print(self.jobId2Num)
        print(self.jobId2Flows)

        prob.solve()

        print(LpStatus[prob.status])

        for v in prob.variables():
            print(v.name, "=", v.varValue)
            if "B" in str(v.name):
                result.addFirstRunResult(str(v.name) + " = " + str(v.varValue))

        return result



    def testFromFile(self, fileName):
        prob = LpProblem("cms-problem", LpMaximize)

        prob += self.bsmall

        self.setGlobalVars(fileName)
        self.setRSAConstraints(prob)
        self.setBijkAndBsmall(prob)

        print(self.bijkName2bijkVar)
        print(self.jobId2DataSize)
        print(self.jobId2Num)
        print(self.jobId2Flows)

        prob.solve()

        print(LpStatus[prob.status])

        for v in prob.variables():
            print(v.name, "=", v.varValue)


if __name__ == '__main__':
    test = SimplifiedScheduler()

    d1 = RsaDataSize()
    d1.readFile("file1")

    #test.testFromFile("file1")

    firstRunResult = test.getFirstRunResult(d1)
    print(firstRunResult.getLines())
