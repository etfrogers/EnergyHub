import datetime

import pickle
from typing import Sequence, Union

from energyhub.config import config
from yrpy import yr_client

_SUN_DATA = {}


class SolarDay:
    def __init__(self, date):
        self.date: datetime.date = date
        api_data = yr_client.get_sun_data(date, config.site_location)
        self.sunrise: datetime.datetime = yr_client.yr_time_to_datetime(api_data['sunrise']['time'], date)
        self.sunset: datetime.datetime = yr_client.yr_time_to_datetime(api_data['sunset']['time'], date)
        self.solar_noon: datetime.datetime = yr_client.yr_time_to_datetime(api_data['solarnoon']['time'], date)

    def __repr__(self):
        return f'SolarDay({self.date})'


def get_sun_data(date: Union[datetime.date, Sequence[datetime.date]]):
    try:
        return [_get_single_sun_data(d) for d in date]
    except TypeError as err:
        if str(err).endswith("object is not iterable"):
            return _get_single_sun_data(date)
        else:
            raise err


def save_sun_data():
    with open(f'{yr_client.CACHEDIR}/sunrise_data.pkl', 'wb') as file:
        pickle.dump(_SUN_DATA, file)


def load_sun_data():
    try:
        with open(f'{yr_client.CACHEDIR}/sunrise_data.pkl', 'rb') as file:
            global _SUN_DATA
            _SUN_DATA = pickle.load(file)
    except (FileNotFoundError, EOFError):
        # cache is missing or corrupt. Proceed without cache.
        pass


def _get_single_sun_data(date: datetime.date) -> SolarDay:
    try:
        data = _SUN_DATA[date]
    except KeyError:
        data = SolarDay(date)
        _SUN_DATA[date] = data
        save_sun_data()
    return data


load_sun_data()
