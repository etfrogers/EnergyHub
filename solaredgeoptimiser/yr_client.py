import json
import datetime
from typing import Tuple
from urllib.parse import urljoin
import logging

import requests

from solaredgeoptimiser.config import config, TIMESTAMP, LOG_TIME_FORMAT

YR_DATE_FORMAT = '%Y-%m-%d'
YR_TIME_FORMAT = f'{YR_DATE_FORMAT}T%H:%M:%SZ'
YR_BASE_URL = 'https://api.met.no/'
YR_FORECAST_URL = f'{YR_BASE_URL}weatherapi/locationforecast/2.0/'
YR_SUNRISE_URL = f'{YR_BASE_URL}weatherapi/sunrise/2.0/'
PROJECT_ID = 'https://github.com/etfrogers/SolarEdge'
USER_AGENT = {'User-agent': PROJECT_ID}

logger = logging.getLogger(__name__)


def get_forecast(location: dict, forecast_style: str = 'compact'):
    # forecast_style = 'compact'
    url = urljoin(YR_FORECAST_URL, forecast_style)
    response = requests.get(url, headers=USER_AGENT, params=location)
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


def get_sunrise_sunset(location: dict, date: datetime.date) -> Tuple[datetime.datetime, ...]:
    params = location.copy()
    params['date'] = date.strftime(YR_DATE_FORMAT)
    params['offset'] = get_local_time_offset_string()
    result = requests.get(YR_SUNRISE_URL+'.json', headers=USER_AGENT, params=params)
    data = json.loads(result.text)
    sun_data = data['location']['time'][0]
    time_strings = (sun_data['sunrise']['time'], sun_data['sunset']['time'])
    offset_str = get_local_time_offset_string()
    assert all(s.endswith(offset_str) for s in time_strings)
    time_strings = [s[:-len(offset_str)] for s in time_strings]
    times = tuple(datetime.datetime.strptime(s, YR_TIME_FORMAT[:-1]) for s in time_strings)
    return times


def get_local_time_offset_string():
    offset = datetime.datetime.now().astimezone().utcoffset()
    sign = '-' if offset < datetime.timedelta(0) else '+'
    offset_str = str(offset)
    h, m, s = (int(part) for part in offset_str.split(':'))
    return f'{sign}{h:02d}:{m:02d}'
