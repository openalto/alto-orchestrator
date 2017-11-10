import logging


def init_logger():
    FORMAT = '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
    logging.basicConfig(format=FORMAT)
    logger = logging.getLogger('orchestrator')
    logger.setLevel(logging.DEBUG)
    return logger


logger = init_logger()
