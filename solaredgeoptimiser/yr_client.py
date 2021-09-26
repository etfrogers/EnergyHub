import json
import datetime
from urllib.parse import urljoin
import logging

import requests

from solaredgeoptimiser.config import config, TIMESTAMP, LOG_TIME_FORMAT

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
    json_forecast = json.loads(response.text)
    # TODO write conditionally?
    with open(f'forecast_{TIMESTAMP}.json', 'w') as file:
        json.dump(json_forecast, file, indent=4)
    return json_forecast


def get_cloud_cover(forecast: dict, start_time: datetime.datetime, end_time: datetime.datetime):
    logger.debug(f'Getting cloud coverage between {start_time.strftime(LOG_TIME_FORMAT)} '
                 f'to {end_time.strftime(LOG_TIME_FORMAT)}')
    coverage = {}
    for timepoint in forecast['properties']['timeseries']:
        time = datetime.datetime.strptime(timepoint["time"], YR_TIME_FORMAT)
        cloud_cover = timepoint["data"]["instant"]["details"]["cloud_area_fraction"]
        logger.debug(f'{time}: cloud cover {cloud_cover}%')
        coverage[time] = cloud_cover
    coverage = {t: c for t, c in coverage.items() if start_time <= t <= end_time}
    logger.debug(coverage)
    if len(coverage) == 0:
        logger.info('No coverage found for the time period')
        return None
    average_coverage = sum(coverage.values()) / len(coverage)
    logger.debug(f'Average coverage: {average_coverage:.2f}%')
    return average_coverage, coverage
