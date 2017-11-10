from alto.unicorn.logger import logger
from alto.unicorn.models.constraints import Constraint


class Scheduler(object):
    def __init__(self, constraints):
        self._constraints = constraints  # type: list[Constraint]

    def schedule(self):
        logger.info("Start scheduling")
        # TODO: make a scheduler
        pass
