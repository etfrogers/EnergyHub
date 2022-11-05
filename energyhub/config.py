import datetime
import inspect
import logging
import os.path
import sys
from typing import List

import yaml

LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIMESTAMP = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


class Config:
    def __init__(self, yaml_data: dict):
        # for key, value in yaml_data.items():
        #     setattr(self, self.key_to_attr(key), value)
        #     print(f"self.{self.key_to_attr(key)} = yaml_data['{key}']")
        # self.solar_edge_api_key = yaml_data['solar-edge']['api-key']
        # self.solar_edge_site_id = yaml_data['solar-edge-site-id']
        # self.solar_edge_account_id = yaml_data['solar-edge-account-id']
        # self.storage_profile_name = yaml_data['storage-profile-name']
        self.site_location = yaml_data['site-location']
        self.peak_time = yaml_data['peak-time']
        self.overnight_usage = yaml_data['overnight-usage']
        self.minimum_battery_level = yaml_data['minimum-battery-level']
        self.reserve_capacity = yaml_data['reserve-capacity']

        self.peak_time = self.to_times(self.peak_time)
        self._data = yaml_data

    @property
    def data(self):
        return self._data

    def __getitem__(self, item):
        return getattr(self, self.key_to_attr(item))

    @property
    def target_battery_level_evening(self):
        return self.min_morning_charge + self.overnight_usage

    @property
    def min_morning_charge(self):
        return self.minimum_battery_level + self.reserve_capacity

    @staticmethod
    def to_times(str_list: List[str]) -> List[datetime.time]:
        return [datetime.time.fromisoformat(t) for t in str_list]

    @staticmethod
    def key_to_attr(key: str) -> str:
        return key.replace('-', '_')

    @staticmethod
    def attr_to_key(attr: str) -> str:
        return attr.replace('_', '-')


def load_config() -> Config:
    with open("site_config.yml", 'r') as file:
        config_data = yaml.safe_load(file)
    return Config(config_data)


def setup_logging():
    logger_ = logging.getLogger('solaredgeoptimiser')
    logger_.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    logger_.addHandler(console)
    # filedir = os.path.dirname(inspect.getsourcefile(lambda: 0))
    # file = logging.FileHandler(f"{filedir}/logs/battery_optimiser.log", mode='a')
    # file.setFormatter(formatter)
    # file.setLevel(logging.INFO)
    # logger_.addHandler(file)
    return logger_


logger = setup_logging()
config = load_config()
