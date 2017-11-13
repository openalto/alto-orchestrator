from alto.unicorn.logger import logger
from alto.unicorn.models.constraints import Constraint
from alto.unicorn.scheduler.simplifiedscheduler import SimplifiedScheduler
from alto.unicorn.scheduler.increasemaxflow import IncreaseMaxFlowScheduler
from alto.unicorn.scheduler.schedulerdataformat import *


class Scheduler(object):
    def __init__(self, constraints):
        self._constraints = constraints  # type: list[Constraint]

        self._IPPort2HostId = {} # hostId starts from 0

        self._HostId2IPPort = {}

        self.__initializeIP2HostId2IP()

        self._jobId2DataSize = {}

        self._flowname2flowid = {}

    def schedule(self):
        logger.info("Start scheduling")
        # TODO: make a scheduler

        firstRun = SimplifiedScheduler()

        firstInputData = RsaDataSize()

        for constraint in self._constraints:
            consStr = self.__getFormedStrFromConstraint(constraint)
            firstInputData.addRSAConstraint(consStr)

        firstInputData.addDataSize(self.__getDataSize())

        firstRunResult = firstRun.getFirstRunResult(firstInputData)


        secondRun = IncreaseMaxFlowScheduler()

        finalResult = secondRun.getResult(firstInputData, firstRunResult)

        return finalResult.getResult()


    def getFlowIdFromFlowname(self, flowname):
        return self._flowname2flowid[flowname]


    def __handleFinalResult(self, finalResult):
        flowname2bw = finalResult.getResult()
        for flowname in flowname2bw:
            jobId = int(str(flowname).split("_")[1])
            srcHostId = str(flowname).split("_")[2]
            dstHostId = str(flowname).split("_")[3]

            localIP = str(self._HostId2IPPort[dstHostId]).split(":")[0]
            localPort = int(self._HostId2IPPort[dstHostId]).split(":")[1]

            remoteIP = str(self._HostId2IPPort[srcHostId]).split(":")[0]
            remotePort = int(self._HostId2IPPort[srcHostId]).split(":")[1]

            # double to int
            rate = int(flowname2bw[flowname])

            self.__setJob(jobId, localIP, localPort, remoteIP, remotePort, rate)


    def __setJob(self, jobId, localIP, localPort, remoteIP, remotePort, filename, rate):
        pass


    #0=600 1=870 2=780 3=890 4=450
    def __getDataSize(self):
        dataSizeStr = ""
        for jobId in self._jobId2DataSize:
            pairStr = str(jobId) + "=" + str(self._jobId2DataSize[jobId])
            dataSizeStr += pairStr + " "
        dataSizeStr = dataSizeStr[:-1]
        return dataSizeStr



    def __initializeIP2HostId2IP(self):
        existingIPPorts = []

        for constraint in self._constraints:
            terms = constraint.terms
            for term in terms:
                flow = term.flow
                srcIp = flow.src_ip
                srcPort = flow.src_port
                dstIp = flow.dst_ip
                dstPort = flow.dst_port

                srcIPPort = str(srcIp) + ":" + str(srcPort)
                dstIPPort = str(dstIp) + ":" + str(dstPort)

                if srcIPPort not in existingIPPorts:
                    hostId = len(existingIPPorts)
                    existingIPPorts.append(srcIPPort)
                    self._HostId2IPPort[hostId] = srcIPPort
                    self._IPPort2HostId[srcIPPort] = hostId
                if dstIPPort not in existingIPPorts:
                    hostId = len(existingIPPorts)
                    existingIPPorts.append(dstIPPort)
                    self._HostId2IPPort[hostId] = dstIPPort
                    self._IPPort2HostId[dstIPPort] = hostId



    def __getFormedStrFromConstraint(self, constraint):
        terms = constraint.terms
        bw = constraint.bound

        leftStr = ""
        for term in terms:
            bijkStr = self.__getBIJKStrFromTerm(term)
            self._flowname2flowid[bijkStr] = term.flow.flow_id
            leftStr += bijkStr + " "

        return leftStr + str(bw)


    def __handleJob(self, job):
        jobId = job.job_id
        datasize = job.file_size

        self._jobId2DataSize[jobId] = datasize


    def __getBIJKStrFromTerm(self, term):
        flow = term.flow
        job = term.job

        self.__handleJob(job)

        srcIP = flow.src_ip
        srcPort = flow.src_port

        srcHostId = self._IPPort2HostId[str(srcIP) + ":" + str(srcPort)]

        dstIP = flow.dst_ip
        dstPort = flow.dst_port

        dstHostId = self._IPPort2HostId[str(dstIP) + ":" + str(dstPort)]

        return "B_" + str(job.job_id) + "_" + str(srcHostId) + "_" + str(dstHostId)
