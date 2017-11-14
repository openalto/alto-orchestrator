from subprocess import Popen, PIPE
import fileinput
import re
import Pyro4
import sys
import os
import time
import shutil


MAX_RATELIMIT = 90 * 1000 * 1000


"""
all qos for an interface should be specified in the same conf file
different interfaces can use different conf file
"""
class FdtClient:

    NUM_STREAM = 32 #only transfer port

    def __init__(self, jobId, srcIp, dstIp, fileName, fdtJarLocation, interface, remotePort):
        self.jobId = jobId
        self.srcIp = srcIp
        self.dstIp = dstIp
        self.remotePort = remotePort
        self.fdtJarLocation = fdtJarLocation
        self.fileName = fileName
        self.interface = interface
        self.qosfilename = "./fireqos-confs/fireqos-" + str(interface) +".conf" # should be shared with different clients

        self.clientPorts = []  #includes control port



    #interface eno1 world-out in rate 10mbit
    #   class job1 commit 6mbit max 8mbit
    #      match4 src 172.27.239.196
    def __generateQosConfFile(self, interface, speed):
        if not os.path.exists(self.qosfilename):
            f = open(self.qosfilename, 'w', newline='\n')
            f.write("interface " + str(interface) + " world-out-" + str(interface) + " out rate " + str(speed) + "\n")
            f.flush()
            f.close()



    #classname = jobID + clientport
    #class c1 commit 26214400kbit max 15728640kbit
    #  match dst 10.10.14.7 sport 57464
    def __addClass(self, dstip, clientPort, rate):
        classname = str(self.jobId) + "_" + str(clientPort)
        f = open(self.qosfilename, 'a')
        f.write("   class " + str(classname) + " commit " + str(rate) + "kbit" + " max " + str(rate) + "kbit\n")
        f.write("      match4 dst " + str(dstip) + " sport " + str(clientPort) + "\n")
        #f.write("      match tcp dports " + str(clientPort))
        f.flush()
        f.close()


    def __changeRateForClass(self, clientPort, newrate):
        classname = str(self.jobId) + "_" + str(clientPort)
        for line in fileinput.input(self.qosfilename, inplace=1):
            if classname in line:
                #update rate to new rate
                ratePattern = re.compile("[0-9]+(bps|kbps|Kbps|mbps|Mbps|gbps|Gbps|bit|kbit|Kbit|mbit|Mbit|gbit|Gbit)")
                rate = ratePattern.findall(line)[0]
                newLine = str(line).replace(rate, newrate)
                print(newLine, end='')
            else:
                #no modification
                print(line, end='')



    #java -jar fdt.jar -c 10.10.14.6 -P 33 -wCount 100 -pull -d /dev/null /dev/zero
    def startClient(self, interfaceSpeed, alreadyUsedPorts):
        p = Popen(['java', '-jar', self.fdtJarLocation, '-c', self.dstIp, '-P', str(FdtClient.NUM_STREAM), '-wCount', '100', '-d',
                   "/dev/null", self.fileName])

        while len(self.clientPorts) < FdtClient.NUM_STREAM + 1:
            time.sleep(2)
            self.__setClientPorts(alreadyUsedPorts)

        print("start to generate qos file")
        self.__generateQosConfFile(self.interface, interfaceSpeed)
        print("started fdt")
        return self.clientPorts


    def __getControlPort(self):
        min = 99999
        for port in self.clientPorts:
            if int(port) < min:
                min = int(port)
        return min


    #tcp6       0      0 [UNKNOWN]:57052         qn-in-xbd.1e100.n:https ESTABLISHED -
    def __setClientPorts(self, alreadyUsedPorts):
        print("start to get netstat")
        proc = Popen(['netstat', '-ntp'], stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        #exitcode = proc.returncode

        out = out.decode("utf-8")

        connections = out.split("\n")

        print("start to analyze connections")

        foreignAddr = str(self.dstIp) + ":" + str(self.remotePort)
        for conn in connections:
            if foreignAddr in conn:
                localConnPattern = re.compile(self.srcIp + ":[0-9]+")
                localConn = localConnPattern.findall(conn)[0]
                port = int(localConn.split(":")[1])
                if port not in self.clientPorts and port not in alreadyUsedPorts:
                    self.clientPorts.append(port)
                    print("add a port: " + str(port))


    def changeRate(self, newRate, isFirstTime):
        eachRate = int(newRate / len(self.clientPorts) - 1)

        for port in self.clientPorts:
            if int(port) == self.__getControlPort():
                continue
            if isFirstTime:
                self.__addClass(self.remoteHost, port, eachRate)
            else:
                self.__changeRateForClass(port, eachRate)

        self.__finishChangeRate()


    def __finishChangeRate(self):
        p = Popen(['fireqos', 'start', self.qosfilename])


@Pyro4.expose
class FdtClientManager:

    def __init__(self):
        self.alreadyusedports = []

        self.jobId2fdtClient = {}

        self.ip2Interface2Speed = {}
        self.__initializeIp2Interface()


    def __initializeIp2Interface(self):
        with open("./ip2interface2rate", "r") as ip2interfaceFile:
            for line in ip2interfaceFile:
                ip = str(line).split(" ")[0]
                interface = str(line).split(" ")[1]
                speed = str(line).split(" ")[2]
                self.ip2Interface2Speed[ip] = interface + " " + speed


    def __fullyUtilize(self):
        p = Popen(['fireqos', 'clear_all_qos'])


    # rate is kbit
    def startDataTransferWithRate(self, jobId, srcIp, dstIp, fileName, rate):
        fdtJarLocation = "./fdt.jar"
        interface = str(self.ip2Interface2Speed[srcIp]).split(" ")[0]
        speed = str(self.ip2Interface2Speed[srcIp]).split(" ")[1]
        remotePort = 54321

        self.__startAll(jobId, srcIp, dstIp, fileName, fdtJarLocation, interface, remotePort, rate, speed)



    def __startAll(self, jobId, srcIp, dstIp, fileName, fdtJarLocation, interface, remotePort, rate, speed):
        if jobId in self.jobId2fdtClient:
            #do not need to create new fdtclient
            fdtClient = self.jobId2fdtClient[jobId]
            if int(rate) > MAX_RATELIMIT:
                self.__fullyUtilize()
            else:
                fdtClient.changeRate(newRate=rate, isFirstTime=False)
            return
        fdtClient = FdtClient(jobId, srcIp, dstIp, fileName, fdtJarLocation, interface, remotePort)
        self.jobId2fdtClient[jobId] = fdtClient
        usedPorts =  fdtClient.startClient(speed, self.alreadyusedports)
        for port in usedPorts:
            self.alreadyusedports.append(port)

        print("already used ports", self.alreadyusedports)
        if int(rate) > MAX_RATELIMIT:
            self.__fullyUtilize()
        else:
            fdtClient.changeRate(newRate=rate, isFirstTime=True)


if __name__ == '__main__':
    #fdt = FdtClient(1, "172.28.229.215", "testfile1.data", "/Users/tony/code/snlab/fdt/", None, None, None)

    #fdt.startClient()

    #fdt.changeRate()

    ip = sys.argv[1]
    port = int(sys.argv[2])

    shutil.rmtree("./fireqos-confs")
    os.makedirs("./fireqos-confs")

    daemon = Pyro4.Daemon(host=ip, port=port)

    fcm = FdtClientManager()
    uri = daemon.register(fcm, objectId="FCM")

    print("Ready. uri = ", uri)  # PYRO:FCM@172.28.229.215:9999
    daemon.requestLoop()