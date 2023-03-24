from datetime import datetime
import json

import requests

"""
Region codes
------------
A – Eastern England
B – East Midlands
C – London
D – Merseyside and Northern Wales
E – West Midlands
F – North Eastern England
G – North Western England
H – Southern England
J – South Eastern England
K – Southern Wales
L – South Western England
M – Yorkshire
N – Southern Scotland
P – Northern Scotland
"""

BASE_URL = "https://api.octopus.energy"
PRODUCT_CODE = "AGILE-18-02-21"
REGION_CODE = 'H'  # Southern England
TARIFF_CODE = f"E-1R-{PRODUCT_CODE}-{REGION_CODE}"
TARIFF_URL = f"{BASE_URL}/v1/products/{PRODUCT_CODE}/electricity-tariffs/{TARIFF_CODE}"
RATE_URL = f"{TARIFF_URL}/standard-unit-rates/"
TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def get_rates(from_: datetime = None, to: datetime = None):
    params = {}
    if from_ is not None:
        params['period_from'] = from_.strftime(TIME_FORMAT)
    if to is not None:
        params['period_to'] = to.strftime(TIME_FORMAT)
    response = requests.get(RATE_URL, params=params)
    json_data = json.loads(response.text)
    rates = [RateTimepoint(result) for result in json_data['results']]
    return rates


def main():
    rates = get_rates()
    for rate in rates:
        print(rate)


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


if __name__ == '__main__':
    main()
