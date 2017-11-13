from subprocess import Popen, PIPE
import fileinput
import re
import Pyro4
import sys

class FdtClient:

    def __init__(self, jobId, remoteHost, fileName, fdtJarLocation, interface, remotePort):
        self.jobId = jobId
        self.remoteHost = remoteHost
        self.remotePort = remotePort
        self.fdtJarLocation = fdtJarLocation
        self.fileName = fileName
        self.interface = interface
        self.qosfilename = 'fireqos.conf'

        self.clientPorts = []



    #interface eno1 world-out in rate 10mbit
    #   class job1 commit 6mbit max 8mbit
    #      match4 src 172.27.239.196
    def __generateQosConfFile(self, interface, speed):
        f = open(self.qosfilename, 'w')
        f.write("interface " + str(interface) + " world-in input rate " + str(speed))
        f.flush()
        f.close()


    #classname = jobID + clientport
    #class c1 commit 26214400kbit max 15728640kbit
    #  match src 10.10.14.7 dport 57464
    def __addClass(self, srcip, clientPort, rate):
        classname = str(self.jobId) + "_" + str(clientPort)
        f = open(self.qosfilename, 'a')
        f.write("   class " + str(classname) + " commit " + str(rate) + " max " + str(rate))
        f.write("      match4 src " + str(srcip) + " dport " + str(clientPort))
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



    #java -jar fdt.jar -c qiao-thinkstation -pull -d ./http.log.fdt ./http.log
    def startClient(self):
        p = Popen(['java', '-jar', self.fdtJarLocation + 'fdt.jar', '-c', self.remoteHost, '-pull', '-d',
                   self.fdtJarLocation + str(self.jobId), './' + self.fileName])

        self.__setCLientPorts()

        self.__generateQosConfFile(self.interface)
        print("started fdt")

    #tcp6       0      0 [UNKNOWN]:57052         qn-in-xbd.1e100.n:https ESTABLISHED -
    def __setClientPorts(self):
        proc = Popen(['netstat', '-ntp'], stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        exitcode = proc.returncode

        connections = out.split("\n")

        for conn in connections:
            foreignAddr = str(self.remoteHost) + ":" + str(self.remotePort)
            if foreignAddr in conn:
                localConnPattern = re.compile("127\.0\.0\.1:[0-9]+")
                localConn = localConnPattern.findall(conn)[0]
                port = int(localConn.split(":")[1])
                self.clientPorts.append(port)


    def changeRate(self, newRate):
        eachRate = newRate / len(self.clientPorts)

        for port in self.clientPorts:
            self.__changeRateForClass(port, eachRate)


    def getReceivedDataSize(self):
        return

@Pyro4.expose
class FdtClientManager:

    def __init__(self):
        self.jobId2fdtClient = {}

        self.ip2Interface = {}
        self.__initializeIp2Interface()


    def __initializeIp2Interface(self):
        with open("./ip2interface", "r") as ip2interfaceFile:
            for line in ip2interfaceFile:
                ip = str(line).split(" ")[0]
                interface = str(line).split(" ")[1]
                self.ip2Interface[ip] = interface


    def startDataTransferWithRate(self, jobId, remoteHost, localHost, fileName, rate):
        fdtJarLocation = "./fdt.jar"
        interface = self.ip2Interface[localHost]
        remotePort = 54321

        fdtClient = self.__getAFdtClient(jobId, remoteHost, fileName, fdtJarLocation, interface, remotePort)
        fdtClient.changeRate(rate)



    def __getAFdtClient(self, jobId, remoteHost, fileName, fdtJarLocation, interface, remotePort):
        if jobId in self.jobId2fdtClient:
            #do not need to create new fdtclient
            return self.jobId2fdtClient[jobId]
        fdtClient = FdtClient(jobId, remoteHost, fileName, fdtJarLocation, interface, remotePort)
        self.jobId2fdtClient[jobId] = fdtClient
        return fdtClient


if __name__ == '__main__':
    #fdt = FdtClient(1, "172.28.229.215", "testfile1.data", "/Users/tony/code/snlab/fdt/", None, None, None)

    #fdt.startClient()

    #fdt.changeRate()

    ip = sys.argv[1]
    port = int(sys.argv[2])

    daemon = Pyro4.Daemon(host=ip, port=port)
    uri = daemon.register(FdtClientManager, objectId="FCM")

    print("Ready. uri = ", uri)  # PYRO:FCM@172.28.229.215:9999
    daemon.requestLoop()