from alto.unicorn.logger import logger
import Pyro4

class DTNController(object):

    @staticmethod
    def start_transfer(self, transfer):
        """
        transfer: {
            "ingress-point": str,
            "flow": Flow,
            "src-dtn-mgmt-ip": str,
            "dst-dtn-mgmt-ip": str,
            "bandwidth": double, "kbit"
        }
        """
        logger.debug("Applying (job: %d) transfer %s -> %s to dtn %s with rate %d" % (
            transfer['flow'].job_id, transfer['flow'].src_ip, transfer['flow'].dst_ip,
            transfer['dst-dtn-mgmt-ip'], transfer['bandwidth']
        ))

        # PYRO:FCM@172.28.229.215:9999
        uri = "PYRO:FCM@" + transfer['dst-dtn-mgmt-ip'] + ":9999"

        fdtClientManager = Pyro4.Proxy(uri)

        flow = transfer['flow']
        jobId = flow._job_id
        remoteHost = flow.src_ip
        fileName = "/dev/zero"
        localHost = flow.dst_ip

        rate = int(transfer['bandwidth'])

        #def startDataTransferWithRate(self, jobId, remoteHost, localHost, fileName, rate):
        fdtClientManager.startDataTransferWithRate(jobId, remoteHost, localHost, fileName, rate)