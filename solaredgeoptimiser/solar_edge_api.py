import json
import logging
from typing import Dict
from urllib.parse import urljoin

import requests

from solaredgeoptimiser.config import config

API_URL = 'https://monitoringapi.solaredge.com'
logger = logging.getLogger(__name__)


def get_power_flow():
    data = api_request('currentPowerFlow')
    logger.debug(data)


def api_request(function: str) -> Dict:
    url = '/'.join((API_URL, 'site', str(config['solar-edge-site-id']), function))
    params = {'api_key': config['solar-edge-api-key']}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return json.loads(response.text)
