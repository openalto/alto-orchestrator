import logging


def init_logger():
    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(format=FORMAT)
    logger = logging.getLogger('orchestrator')
    logger.warning('Protocol problem: %s', 'connection reset')
    return logger


logger = init_logger()
