import datetime
import json
import logging
from typing import Dict

import requests

from solaredgeoptimiser.config import config

API_URL = 'https://monitoringapi.solaredge.com'
API_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
logger = logging.getLogger(__name__)


class BatteryNotFoundError(Exception):
    pass


def get_power_flow():
    data = api_request('currentPowerFlow')
    logger.debug(data)


def get_battery_level():
    logger.debug('Getting battery level')
    start_time = datetime.datetime.now() - datetime.timedelta(minutes=15)
    end_time = datetime.datetime.now() + datetime.timedelta(minutes=15)
    params = {'startTime': start_time.strftime(API_TIME_FORMAT),
              'endTime': end_time.strftime(API_TIME_FORMAT)}
    data = api_request('storageData', params)
    logger.debug(data)
    n_batteries = data['storageData']['batteryCount']
    if n_batteries != 1:
        msg = f'Expected 1 battery, but found {n_batteries}'
        logger.error(msg)
        raise BatteryNotFoundError(msg)
    charge = data['storageData']['batteries'][0]['telemetries'][-1]['batteryPercentageState']
    logger.debug(f'Battery charge is {charge}')
    return charge


def api_request(function: str, params: dict = None) -> Dict:
    if params is None:
        params = {}
    params['api_key'] = config['solar-edge-api-key']
    url = '/'.join((API_URL, 'site', str(config['solar-edge-site-id']), function))
    response = requests.get(url, params=params)
    response.raise_for_status()
    return json.loads(response.text)
