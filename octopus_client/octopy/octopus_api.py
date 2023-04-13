from datetime import datetime, date, time, timedelta
import json
from typing import List

import requests

from SolarEdgeClient.solaredge.solar_edge_api import day_start_end_times

REGION_CODES = {
    'A': 'Eastern England',
    'B': 'East Midlands',
    'C': 'London',
    'D': 'Merseyside and Northern Wales',
    'E': 'West Midlands',
    'F': 'North Eastern England',
    'G': 'North Western England',
    'H': 'Southern England',
    'J': 'South Eastern England',
    'K': 'Southern Wales',
    'L': 'South Western England',
    'M': 'Yorkshire',
    'N': 'Southern Scotland',
    'P': 'Northern Scotland',
}

BASE_URL = "https://api.octopus.energy"
PRODUCT_CODE = "AGILE-18-02-21"
EXPORT_PRODUCT_CODE = "AGILE-OUTGOING-19-05-13"
REGION_CODE = 'H'  # Southern England
TARIFF_CODE = f"E-1R-{PRODUCT_CODE}-{REGION_CODE}"
EXPORT_TARIFF_CODE = f"E-1R-{EXPORT_PRODUCT_CODE}-{REGION_CODE}"
TARIFF_URL = f"{BASE_URL}/v1/products/{PRODUCT_CODE}/electricity-tariffs/{TARIFF_CODE}"
RATE_URL = f"{TARIFF_URL}/standard-unit-rates/"
EXPORT_TARIFF_URL = f"{BASE_URL}/v1/products/{EXPORT_PRODUCT_CODE}/electricity-tariffs/{EXPORT_TARIFF_CODE}"
EXPORT_RATE_URL = f"{EXPORT_TARIFF_URL}/standard-unit-rates/"

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
METER_CONSUMPTION_URL = BASE_URL + '/v1/electricity-meter-points/{mpan}/meters/{serial_number}/consumption/'


class MeterTimepoint:
    def __init__(self, result):
        self.from_time = datetime.strptime(result['interval_start'], TIME_FORMAT)
        self.to_time = datetime.strptime(result['interval_end'], TIME_FORMAT)
        self.value = result['consumption']

    def __str__(self):
        return f"{self.from_time.strftime('%d/%m/%Y %H:%M')}-" \
               f"{self.to_time.strftime('%H:%M')}  {self.value:.2f}kWh"

    def __repr__(self):
        return str(self)


class RateTimepoint:
    def __init__(self, result):
        self.from_time = datetime.strptime(result['valid_from'], TIME_FORMAT)
        self.to_time = datetime.strptime(result['valid_to'], TIME_FORMAT)
        self.price_exc_vat = result['value_exc_vat']
        self.price_inc_vat = result['value_inc_vat']

    def __str__(self):
        return f"{self.from_time.strftime('%d/%m/%Y %H:%M')}-" \
               f"{self.to_time.strftime('%H:%M')}  {self.price_inc_vat:.2f}p"

    def __repr__(self):
        return str(self)


class OctopusClient:
    def __init__(self, region_code: str,
                 api_key: str = '',
                 consumption_mpan: str = '', consumption_serial: str = '',
                 export_mpan: str = '', export_serial: str = '',
                 ):
        if region_code not in REGION_CODES:
            # try an inverse lookup on region name
            if region_code in REGION_CODES.values():
                found_codes = [key for key, val in REGION_CODES.items() if val == region_code]
                assert len(found_codes) == 1
                region_code = found_codes[0]
            else:
                raise ValueError('Invalid region code')
        self.region_code = region_code
        self.api_key = api_key
        self.consumption_mpan = consumption_mpan
        self.consumption_serial = consumption_serial
        self.export_mpan = export_mpan
        self.export_serial = export_serial

    @property
    def consumption_meter_url(self):
        return METER_CONSUMPTION_URL.format(mpan=self.consumption_mpan, serial_number=self.consumption_serial)

    @property
    def export_meter_url(self):
        return METER_CONSUMPTION_URL.format(mpan=self.export_mpan, serial_number=self.export_serial)

    def api_call(self, url, from_: datetime = None, to: datetime = None):
        params = {}
        if from_ is not None:
            params['period_from'] = from_.strftime(TIME_FORMAT)
        if to is not None:
            params['period_to'] = to.strftime(TIME_FORMAT)
        kwargs = {}
        if self.api_key:
            kwargs['auth'] = (self.api_key, '')
        response = requests.get(url, params=params, **kwargs)
        json_data = json.loads(response.text)
        return json_data

    def get_rates(self, from_: datetime = None, to: datetime = None) -> List[RateTimepoint]:
        data = self.api_call(RATE_URL, from_, to)
        rates = [RateTimepoint(result) for result in data['results']]
        return rates

    def get_export_rates(self, from_: datetime = None, to: datetime = None) -> List[RateTimepoint]:
        data = self.api_call(EXPORT_RATE_URL, from_, to)
        rates = [RateTimepoint(result) for result in data['results']]
        return rates

    def get_rates_for_day(self, day: date) -> List[RateTimepoint]:
        return self.get_rates(*day_start_end_times(day))

    def get_export_rates_for_day(self, day: date) -> List[RateTimepoint]:
        return self.get_export_rates(*day_start_end_times(day))

    def get_consumption(self, from_: datetime = None, to: datetime = None) -> List[MeterTimepoint]:
        data = self.api_call(self.consumption_meter_url, from_, to)
        return [MeterTimepoint(result) for result in data['results']]

    def get_consumption_for_day(self, day: date) -> List[MeterTimepoint]:
        return self.call_func_for_day(day, self.get_consumption)

    def get_export(self, from_: datetime = None, to: datetime = None) -> List[MeterTimepoint]:
        data = self.api_call(self.export_meter_url, from_, to)
        return [MeterTimepoint(result) for result in data['results']]

    @staticmethod
    def call_func_for_day(day: date, func: callable):
        start, end = day_start_end_times(day)
        data = func(start, end)
        return data

    def get_export_for_day(self, day: date) -> List[MeterTimepoint]:
        return self.call_func_for_day(day, self.get_export)


def main():
    rates = OctopusClient(region_code='H').get_rates()
    for rate in rates:
        print(rate)


if __name__ == '__main__':
    main()
