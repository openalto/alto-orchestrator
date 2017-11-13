from alto.unicorn.logger import logger

class DTNController(object):

    @staticmethod
    def start_transfer(self, transfer):
        """
        transfer: {
            "ingress-point": str,
            "flow": Flow,
            "src-dtn-mgmt-ip": str,
            "dst-dtn-mgmt-ip": str,
            "bandwidth": int
        }
        """
        logger.debug("Applying (job: %d) transfer %s -> %s to dtn %s with rate %d" % (
            transfer['flow'].job_id, transfer['flow'].src_ip, transfer['flow'].dst_ip,
            transfer['dst-dtn-mgmt-ip'], transfer['bandwidth']
        ))
        pass