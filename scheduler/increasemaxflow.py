from pulp import *


bijkName2PlusVar = {}

bijkName2MinusVar = {}

rsaCs = []

jobId2DataSize = {}

bsmall = LpVariable("bsmall", 0)

jobId2Flows = {}

flowName2BasicBw = {}

jobId2MaxFlowName = {}

jobId2MultiMaxFlowName = {}


def setupAllGlobalVars():
    global bijkName2PlusVar
    global bijkName2MinusVar
    global rsaCs
    global jobId2DataSize
    global bsmall
    global jobId2Flows
    global flowName2BasicBw
    global jobId2MaxFlowName
    global jobId2MultiMaxFlowName

    bijkName2PlusVar = {}

    bijkName2MinusVar = {}

    rsaCs = []

    jobId2DataSize = {}

    bsmall = LpVariable("bsmall", 0)

    jobId2Flows = {}

    flowName2BasicBw = {}

    jobId2MaxFlowName = {}

    jobId2MultiMaxFlowName = {}


#after set jobId2MaxFlowName
def setJobId2MultiMaxFlowName():
    #handle flowName2BasicBw
    for flowName in flowName2BasicBw:
        jobId = str(flowName).split("_")[1]
        if jobId in jobId2MultiMaxFlowName:
            if flowName2BasicBw[flowName] == flowName2BasicBw[jobId2MaxFlowName[jobId]]:
                jobId2MultiMaxFlowName[jobId].append(flowName)
        else:
            if flowName2BasicBw[flowName] == flowName2BasicBw[jobId2MaxFlowName[jobId]]:
                jobId2MultiMaxFlowName[jobId] = [flowName]


globalRound = 0


def setOneCombinationFromMMFNBasedGlobalRound():
    global globalRound
    print("global round: " + str(globalRound))
    for jobId in jobId2MultiMaxFlowName:
        jobId2MaxFlowName[jobId] = jobId2MultiMaxFlowName[jobId][0]
    maxRoundNum = sum(len(jobId2MultiMaxFlowName[x]) for x in jobId2MultiMaxFlowName)
    print(maxRoundNum)
    if globalRound >= maxRoundNum:
        globalRound = -1
    else:
        tempRound = globalRound
        for jobId in jobId2MultiMaxFlowName:
            mod = tempRound % len(jobId2MultiMaxFlowName[jobId])
            jobId2MaxFlowName[jobId] = jobId2MultiMaxFlowName[jobId][int(mod)]
            tempRound -= mod
            tempRound /= len(jobId2MultiMaxFlowName[jobId])
            if tempRound < 0:
                break




def setGlobalVars(filename, filename2):
    flow2JobId = {}
    with open(filename) as f:
        for line in f:
            if str(line).__contains__("B"):
                rsaCs.append(line)
                flows = str(line).split(" ")[:-1]
                for flow in flows:
                    flow2JobId[flow] = str(flow).split("_")[1]
            else:
                jobId2DataSizeStr = str(line).split(" ")
                for j2d in jobId2DataSizeStr:
                    jobId = str(j2d).split("=")[0]
                    dataSize = str(j2d).split("=")[1]
                    jobId2DataSize[jobId] = dataSize
    for flow in flow2JobId:
        jobId = str(flow).split("_")[1]
        if jobId not in jobId2Flows:
            jobId2Flows[jobId] = [flow]
        else:
            jobId2Flows[jobId].append(flow)
    with open(filename2) as f:
        for line in f:
            tempLine = line.replace(" ", "")
            flowName = tempLine.split("=")[0]
            allocDouble = float(tempLine.split("=")[1])
            flowName2BasicBw[flowName] = allocDouble
    for flowName in flowName2BasicBw:
        jobId = str(flowName).split("_")[1]
        if jobId in jobId2MaxFlowName:
            if flowName2BasicBw[jobId2MaxFlowName[jobId]] < flowName2BasicBw[flowName]:
                jobId2MaxFlowName[jobId] = flowName
        else:
            jobId2MaxFlowName[jobId] = flowName
    setJobId2MultiMaxFlowName()
    setOneCombinationFromMMFNBasedGlobalRound()




def onlyOneFlowNameWithNonZeroBwAlloc(flowNames):
    count = 0
    for flowName in flowNames:
        bwAlloc = flowName2BasicBw[flowName]
        if bwAlloc > 0:
            count += 1
    if count > 1:
        return False
    else:
        return True


def setPlusMinusVars():
    for jobId in jobId2Flows:
        flowNames = jobId2Flows[jobId]
        if onlyOneFlowNameWithNonZeroBwAlloc(flowNames):
            flowNameWithMaxBw = jobId2MaxFlowName[jobId]
            var = LpVariable("minus-" + flowNameWithMaxBw, 0, flowName2BasicBw[flowNameWithMaxBw])
            bijkName2MinusVar[flowNameWithMaxBw] = var
        else:
            flowNameWithMaxBw = jobId2MaxFlowName[jobId]
            var = LpVariable("plus-" + flowNameWithMaxBw, 0)
            bijkName2PlusVar[flowNameWithMaxBw] = var
            for flowName in flowNames:
                if flowName != flowNameWithMaxBw and flowName2BasicBw[flowName] > 0:
                    var = LpVariable("minus-" + flowName, 0, flowName2BasicBw[flowName])
                    bijkName2MinusVar[flowName] = var


def setBijkIncVars(prob):
    for rsaC in rsaCs:
        flows = str(rsaC).split(" ")[:-1]
        rightBw = float(str(rsaC).split(" ")[-1])
        minusVars = []
        plusVars = []
        for flow in flows:
            totalBw = 0.0
            if flow in bijkName2MinusVar:
                minusVars.append(bijkName2MinusVar[flow])
            elif flow in bijkName2PlusVar:
                plusVars.append(bijkName2PlusVar[flow])
            totalBw += flowName2BasicBw[flow]
            rightBw -= totalBw
        prob += lpSum(plusVars) - lpSum(minusVars) <= rightBw


def setMaxFlowVar(prob):
    for jobId in jobId2Flows:
        dataSize = int(jobId2DataSize[jobId])
        jobFlowName = jobId2MaxFlowName[jobId]
        if jobFlowName in bijkName2PlusVar:
            prob += dataSize * bsmall == flowName2BasicBw[jobFlowName] + bijkName2PlusVar[jobFlowName]
        else:
            prob += dataSize * bsmall == flowName2BasicBw[jobFlowName] - bijkName2MinusVar[jobFlowName]


if __name__ == '__main__':
    while 1:
        setupAllGlobalVars()

        prob = LpProblem("cms-problem-2", LpMaximize)

        prob += bsmall

        setGlobalVars("file1", "file2")
        setPlusMinusVars()

        setBijkIncVars(prob)
        setMaxFlowVar(prob)

        prob.solve()

        print(LpStatus[prob.status])

        finish = True
        for v in prob.variables():
            #print(v.name, "=", v.varValue)
            if str(v.name).__contains__("plus"):
                if v.varValue == 0.0:
                    finish = False
                    break

        if finish:
            for v in prob.variables():
                print(v.name, "=", v.varValue)
            break

        if globalRound == -1:
            print("cannot find the result")
            break
        else:
            globalRound += 1