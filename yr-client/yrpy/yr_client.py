import inspect
import json
import datetime
import os
import pathlib
from typing import Tuple
from urllib.parse import urljoin
import logging

import requests

from energyhub.config import TIMESTAMP, LOG_TIME_FORMAT

CACHEDIR = pathlib.Path(os.path.dirname(inspect.getsourcefile(lambda: 0))) / '..' / 'cache/'

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
    with open(CACHEDIR / f'forecast_{TIMESTAMP}.json', 'w') as file:
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
    sun_data = get_sun_data(date, location)
    time_strings = (sun_data['sunrise']['time'], sun_data['sunset']['time'])
    times = tuple(yr_time_to_datetime(s, date) for s in time_strings)
    return times


def yr_time_to_datetime(time_string: str, date: datetime.date) -> datetime.datetime:
    offset_str = get_local_time_offset_string(date)
    assert time_string.endswith(offset_str)
    time_string = time_string[:-len(offset_str)]
    return datetime.datetime.strptime(time_string, YR_TIME_FORMAT[:-1])


def get_sun_data(date: datetime.date, location: dict) -> dict:
    data = get_astronomical_data(date, location)
    sun_data = data['location']['time'][0]
    return sun_data


def get_astronomical_data(date: datetime.date, location: dict) -> dict:
    params = location.copy()
    params['date'] = date.strftime(YR_DATE_FORMAT)
    params['offset'] = get_local_time_offset_string(date)
    result = requests.get(YR_SUNRISE_URL + '.json', headers=USER_AGENT, params=params)
    data = json.loads(result.text)
    return data


def get_local_time_offset_string(date: datetime.date = None):
    if date is None:
        date = datetime.datetime.now()
    if isinstance(date, datetime.date):
        # combine with noon to avoid DST errors if midnight is used.
        date = datetime.datetime.combine(date, datetime.time(hour=12, minute=0))
    offset = date.astimezone().utcoffset()
    sign = '-' if offset < datetime.timedelta(0) else '+'
    offset_str = str(offset)
    h, m, s = (int(part) for part in offset_str.split(':'))
    return f'{sign}{h:02d}:{m:02d}'
