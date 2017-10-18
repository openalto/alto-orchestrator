from .entries import RegisterEntry
from .route import set_route

import os
import yaml

current_path = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(current_path, "schema/tasks_schema.yaml")) as f:
    TASKS_SCHEMA = yaml.load(f)