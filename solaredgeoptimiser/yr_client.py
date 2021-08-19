import json
import datetime
from urllib.parse import urljoin
import logging

import requests

from solaredgeoptimiser.config import config


YR_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
YR_API_URL = 'https://api.met.no/weatherapi/locationforecast/2.0/'
PROJECT_ID = 'https://github.com/etfrogers/SolarEdge'

logger = logging.getLogger(__name__)


def get_forecast(location: dict, forecast_style: str = 'compact'):
    user_agent = {'User-agent': PROJECT_ID}
    # forecast_style = 'compact'
    url = urljoin(YR_API_URL, forecast_style)
    response = requests.get(url, headers=user_agent, params=location)
    response.raise_for_status()
    return json.loads(response.text)


def get_cloud_cover(forecast: dict):
    coverage = {}
    for timepoint in forecast['properties']['timeseries']:
        time = datetime.datetime.strptime(timepoint["time"], YR_TIME_FORMAT)
        cloud_cover = timepoint["data"]["instant"]["details"]["cloud_area_fraction"]
        logger.debug(f'{time}: cloud cover {cloud_cover}%')
        coverage[time] = cloud_cover
    start_of_peak_time = config['peak-time'][0]
    end_time = datetime.datetime.combine(datetime.datetime.now(), start_of_peak_time)
    coverage = {t: c for t, c in coverage.items() if t <= end_time}
    average_coverage = sum(coverage.values()) / len(coverage)
    logger.debug(coverage)
    return average_coverage
