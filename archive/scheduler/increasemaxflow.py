from pulp import *
from schedulerdataformat import *


class IncreaseMaxFlowScheduler:


    def __init__(self):
        self.bijkName2PlusVar = {}

        self.bijkName2MinusVar = {}

        self.rsaCs = []

        self.jobId2DataSize = {}

        self.bsmall = LpVariable("bsmall", 0)

        self.jobId2Flows = {}

        self.flowName2BasicBw = {}

        self.jobId2MaxFlowName = {}

        self.jobId2MultiMaxFlowName = {}

        self.globalRound = 0


    def setupAllGlobalVars(self):
        self.bijkName2PlusVar = {}

        self.bijkName2MinusVar = {}

        self.rsaCs = []

        self.jobId2DataSize = {}

        self.bsmall = LpVariable("bsmall", 0)

        self.jobId2Flows = {}

        self.flowName2BasicBw = {}

        self.jobId2MaxFlowName = {}

        self.jobId2MultiMaxFlowName = {}


    def setJobId2MultiMaxFlowName(self):
        #handle flowName2BasicBw
        for flowName in self.flowName2BasicBw:
            jobId = str(flowName).split("_")[1]
            if jobId in self.jobId2MultiMaxFlowName:
                if self.flowName2BasicBw[flowName] == self.flowName2BasicBw[self.jobId2MaxFlowName[jobId]]:
                    self.jobId2MultiMaxFlowName[jobId].append(flowName)
            else:
                if self.flowName2BasicBw[flowName] == self.flowName2BasicBw[self.jobId2MaxFlowName[jobId]]:
                    self.jobId2MultiMaxFlowName[jobId] = [flowName]





    def setOneCombinationFromMMFNBasedGlobalRound(self):
        print("global round: " + str(self.globalRound))
        for jobId in self.jobId2MultiMaxFlowName:
            self.jobId2MaxFlowName[jobId] = self.jobId2MultiMaxFlowName[jobId][0]
        maxRoundNum = sum(len(self.jobId2MultiMaxFlowName[x]) for x in self.jobId2MultiMaxFlowName)
        print(maxRoundNum)
        if self.globalRound >= maxRoundNum:
            self.globalRound = -1
        else:
            tempRound = self.globalRound
            for jobId in self.jobId2MultiMaxFlowName:
                mod = tempRound % len(self.jobId2MultiMaxFlowName[jobId])
                self.jobId2MaxFlowName[jobId] = self.jobId2MultiMaxFlowName[jobId][int(mod)]
                tempRound -= mod
                tempRound /= len(self.jobId2MultiMaxFlowName[jobId])
                if tempRound < 0:
                    break


    def setGlobalVarsFromStruc(self, rsaInput, firstRunResult):
        flow2JobId = {}
        for line in rsaInput.getLines():
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
            if jobId not in self.jobId2Flows:
                self.jobId2Flows[jobId] = [flow]
            else:
                self.jobId2Flows[jobId].append(flow)

        for line in firstRunResult.getLines():
            tempLine = line.replace(" ", "")
            flowName = tempLine.split("=")[0]
            allocDouble = float(tempLine.split("=")[1])
            self.flowName2BasicBw[flowName] = allocDouble

        for flowName in self.flowName2BasicBw:
            jobId = str(flowName).split("_")[1]
            if jobId in self.jobId2MaxFlowName:
                if self.flowName2BasicBw[self.jobId2MaxFlowName[jobId]] < self.flowName2BasicBw[flowName]:
                    self.jobId2MaxFlowName[jobId] = flowName
            else:
                self.jobId2MaxFlowName[jobId] = flowName
        self.setJobId2MultiMaxFlowName()
        self.setOneCombinationFromMMFNBasedGlobalRound()


    def setGlobalVars(self, filename, filename2):
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
            if jobId not in self.jobId2Flows:
                self.jobId2Flows[jobId] = [flow]
            else:
                self.jobId2Flows[jobId].append(flow)
        with open(filename2) as f:
            for line in f:
                tempLine = line.replace(" ", "")
                flowName = tempLine.split("=")[0]
                allocDouble = float(tempLine.split("=")[1])
                self.flowName2BasicBw[flowName] = allocDouble
        for flowName in self.flowName2BasicBw:
            jobId = str(flowName).split("_")[1]
            if jobId in self.jobId2MaxFlowName:
                if self.flowName2BasicBw[self.jobId2MaxFlowName[jobId]] < self.flowName2BasicBw[flowName]:
                    self.jobId2MaxFlowName[jobId] = flowName
            else:
                self.jobId2MaxFlowName[jobId] = flowName
        self.setJobId2MultiMaxFlowName()
        self.setOneCombinationFromMMFNBasedGlobalRound()




    def onlyOneFlowNameWithNonZeroBwAlloc(self, flowNames):
        count = 0
        for flowName in flowNames:
            bwAlloc = self.flowName2BasicBw[flowName]
            if bwAlloc > 0:
                count += 1
        if count > 1:
            return False
        else:
            return True


    def setPlusMinusVars(self):
        for jobId in self.jobId2Flows:
            flowNames = self.jobId2Flows[jobId]
            if self.onlyOneFlowNameWithNonZeroBwAlloc(flowNames):
                flowNameWithMaxBw = self.jobId2MaxFlowName[jobId]
                var = LpVariable("minus-" + flowNameWithMaxBw, 0, self.flowName2BasicBw[flowNameWithMaxBw])
                self.bijkName2MinusVar[flowNameWithMaxBw] = var
            else:
                flowNameWithMaxBw = self.jobId2MaxFlowName[jobId]
                var = LpVariable("plus-" + flowNameWithMaxBw, 0)
                self.bijkName2PlusVar[flowNameWithMaxBw] = var
                for flowName in flowNames:
                    if flowName != flowNameWithMaxBw and self.flowName2BasicBw[flowName] > 0:
                        var = LpVariable("minus-" + flowName, 0, self.flowName2BasicBw[flowName])
                        self.bijkName2MinusVar[flowName] = var


    def setBijkIncVars(self, prob):
        for rsaC in self.rsaCs:
            flows = str(rsaC).split(" ")[:-1]
            rightBw = float(str(rsaC).split(" ")[-1])
            minusVars = []
            plusVars = []
            for flow in flows:
                totalBw = 0.0
                if flow in self.bijkName2MinusVar:
                    minusVars.append(self.bijkName2MinusVar[flow])
                elif flow in self.bijkName2PlusVar:
                    plusVars.append(self.bijkName2PlusVar[flow])
                totalBw += self.flowName2BasicBw[flow]
                rightBw -= totalBw
            prob += lpSum(plusVars) - lpSum(minusVars) <= rightBw


    def setMaxFlowVar(self, prob):
        for jobId in self.jobId2Flows:
            dataSize = int(self.jobId2DataSize[jobId])
            jobFlowName = self.jobId2MaxFlowName[jobId]
            if jobFlowName in self.bijkName2PlusVar:
                prob += dataSize * self.bsmall == self.flowName2BasicBw[jobFlowName] + self.bijkName2PlusVar[jobFlowName]
            else:
                prob += dataSize * self.bsmall == self.flowName2BasicBw[jobFlowName] - self.bijkName2MinusVar[jobFlowName]


    def testFromFile(self, fileName1, fileName2):
        while 1:
            self.setupAllGlobalVars()

            prob = LpProblem("cms-problem-2", LpMaximize)

            prob += self.bsmall

            self.setGlobalVars(fileName1, fileName2)
            self.setPlusMinusVars()

            self.setBijkIncVars(prob)
            self.setMaxFlowVar(prob)

            prob.solve()

            print(LpStatus[prob.status])

            finish = True
            for v in prob.variables():
                # print(v.name, "=", v.varValue)
                if str(v.name).__contains__("plus"):
                    if v.varValue == 0.0:
                        finish = False
                        break

            if finish:
                for v in prob.variables():
                    print(v.name, "=", v.varValue)
                break

            if self.globalRound == -1:
                print("cannot find the result")
                break
            else:
                self.globalRound += 1


    def getResult(self, rsaInput, firstRunInput):
        result = FinalResult()
        while 1:
            self.setupAllGlobalVars()

            prob = LpProblem("cms-problem-2", LpMaximize)

            prob += self.bsmall

            self.setGlobalVarsFromStruc(rsaInput, firstRunInput)
            self.setPlusMinusVars()

            self.setBijkIncVars(prob)
            self.setMaxFlowVar(prob)

            prob.solve()

            print(LpStatus[prob.status])

            finish = True
            for v in prob.variables():
                # print(v.name, "=", v.varValue)
                if str(v.name).__contains__("plus"):
                    if v.varValue == 0.0:
                        finish = False
                        break

            if finish:

                bname2bw = {}
                for line in firstRunInput.getLines():
                    tempLine = line.replace(" ", "")
                    flowName = tempLine.split("=")[0]
                    allocDouble = float(tempLine.split("=")[1])
                    bname2bw[flowName] = allocDouble

                for v in prob.variables():
                    type = str(v.name).split("_")[0]
                    flowName = "_".join(str(v.name).split("_")[1:])
                    if type == "minus":
                        bname2bw[flowName] -= v.varValue
                    elif type == "plus":
                        bname2bw[flowName] += v.varValue

                jobId2maxFlow = {}

                for bname in bname2bw:
                    jobId = str(bname).split("_")[1]
                    if jobId not in jobId2maxFlow:
                        jobId2maxFlow[jobId] = bname
                    elif bname2bw[bname] > bname2bw[jobId2maxFlow[jobId]]:
                        jobId2maxFlow[jobId] = bname


                for jobId in jobId2maxFlow:
                    flowName = jobId2maxFlow[jobId]
                    bw = bname2bw[flowName]
                    result.addFinalResult(flowName, bw)

                return result

            if self.globalRound == -1:
                print("cannot find the result")
                break
            else:
                self.globalRound += 1


if __name__ == '__main__':
    test = IncreaseMaxFlowScheduler()

    #test.testFromFile("demo_file1", "demo_file2")

    d1 = RsaDataSize()
    d1.readFile("demo_file1")

    d2 = FirstRunResult()
    d2.readFile("demo_file2")

    result = test.getResult(d1, d2)

    print(result.getResult())