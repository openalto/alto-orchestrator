class RsaDataSize:

    def __init__(self):
        self.lines = []

    def addRSAConstraint(self, rsaConstraint):
        self.lines.append(rsaConstraint)

    def addDataSize(self, dataSize):
        self.lines.append(dataSize)

    def readFile(self, fileName):
        with open(fileName) as f:
            for line in f:
                self.lines.append(line)

    def getLines(self):
        return self.lines


class FirstRunResult:

    def __init__(self):
        self.lines = []

    def addFirstRunResult(self, firstRunResult):
        self.lines.append(firstRunResult)

    def readFile(self, fileName):
        with open(fileName) as f:
            for line in f:
                self.lines.append(line)

    def getLines(self):
        return self.lines


class FinalResult:

    def __init__(self):
        self.flowname2bw = {}

    def addFinalResult(self, flowname, bw):
        self.flowname2bw[flowname] = bw

    def getResult(self):
        return self.flowname2bw