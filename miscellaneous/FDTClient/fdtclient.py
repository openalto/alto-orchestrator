from subprocess import Popen

class FdtClient:

    def __init__(self, jobId, remoteHost, fileName, fdtJarLocation, interface, remotePort, localPort):
        self.jobId = jobId
        self.remoteHost = remoteHost
        self.currentRate = 0
        self.fdtJarLocation = fdtJarLocation
        self.fileName = fileName

    #java -jar fdt.jar -c qiao-thinkstation -pull -d ./http.log.fdt ./http.log
    def startClient(self, initialRate):
        self.currentRate = initialRate
        p = Popen(['java', '-jar', self.fdtJarLocation + 'fdt.jar', '-c', self.remoteHost, '-pull', '-d',
                   self.fdtJarLocation + str(self.jobId), './' + self.fileName, '-limit', str(self.currentRate) + 'G'])

        print("next step")



    def changeRate(self, newRate):
        return


    def getReceivedDataSize(self):
        return


if __name__ == '__main__':
    fdt = FdtClient(1, "172.28.229.215", "testfile1.data", "/Users/tony/code/snlab/fdt/", None, None, None)

    fdt.startClient(5)