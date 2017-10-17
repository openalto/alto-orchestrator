from pulp import *


bijkName2bijkVar = {}

rsaCs = []

jobId2DataSize = {}

bsmall = LpVariable("bsmall", 0)

jobId2Num = {}

jobId2Flows = {}


def setRSAConstraints(prob):
    for rsaC in rsaCs:
        bijkL = []
        flows = str(rsaC).split(" ")[:-1]
        bw = int(str(rsaC).split(" ")[-1])
        for bijkStr in flows:
            bijk = None
            if bijkStr not in bijkName2bijkVar:
                bijk = LpVariable(bijkStr, 0)
                bijkName2bijkVar[bijkStr] = bijk
            else:
                bijk = bijkName2bijkVar[bijkStr]
            bijkL.append(bijk)
        prob += lpSum(bijkL) <= bw


def setGlobalVars(filename):
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
        if jobId not in jobId2Num:
            jobId2Num[jobId] = 1
        else:
            jobId2Num[jobId] += 1
        if jobId not in jobId2Flows:
            jobId2Flows[jobId] = [flow]
        else:
            jobId2Flows[jobId].append(flow)





def setBijkAndBsmall(prob):
    for jobId in jobId2DataSize:
        Bi = int(jobId2DataSize[jobId]) * bsmall
        #prob += lpSum(bijkName2bijkVar[bijkName] for bijkName in jobId2Flows[jobId]) - Bi * jobId2Num[jobId] == 0
        prob += lpSum(bijkName2bijkVar[bijkName] for bijkName in jobId2Flows[jobId]) - Bi == 0


if __name__ == '__main__':
    prob = LpProblem("cms-problem", LpMaximize)

    prob += bsmall

    setGlobalVars("file1")
    setRSAConstraints(prob)
    setBijkAndBsmall(prob)

    print(bijkName2bijkVar)
    print(jobId2DataSize)
    print(jobId2Num)
    print(jobId2Flows)


    prob.solve()

    print(LpStatus[prob.status])

    for v in prob.variables():
        print(v.name, "=", v.varValue)