"""
Configuration for the predeletion scripts.

This module reads the configuration file "config.yaml" and makes
configuration importable by other modules.
"""

import os
import yaml

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
CONFIG_FILE = os.path.join(BASE_PATH, "config.yaml")
with open(CONFIG_FILE) as f:
    config = yaml.safe_load(f)

REDIS_HOST = config["redis"]["host"]
REDIS_PORT = config["redis"]["port"]
REDIS_DB = config["redis"]["db"]
REDIS_PREFIX = config["redis"]["prefix"]
EXPIREMINS = config["redis"]["expiremins"]
KEY = config["redis"]["key"]
PUBFILEDIR = config["mom"]["pubfiledir"]
