import datetime
import logging
import sys
from typing import List

import yaml

LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIMESTAMP = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


def to_times(str_list: List[str]) -> List[datetime.time]:
    return [datetime.time.fromisoformat(t) for t in str_list]


def load_config() -> dict:
    with open("site_config.yml", 'r') as file:
        config = yaml.safe_load(file)
    config['peak-time'] = to_times(config['peak-time'])
    return config


def setup_logging():
    logger_ = logging.getLogger('solaredgeoptimiser')
    logger_.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    logger_.addHandler(console)

    file = logging.FileHandler("battery_optimiser.log", mode='a')
    file.setFormatter(formatter)
    file.setLevel(logging.INFO)
    logger_.addHandler(file)
    return logger_


logger = setup_logging()
config = load_config()
