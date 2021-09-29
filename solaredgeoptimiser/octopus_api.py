import datetime
import json

import requests

BASE_URL = "https://api.octopus.energy"
PRODUCT_CODE = "AGILE-18-02-21"
TARIFF_CODE = f"E-1R-{PRODUCT_CODE}-C"
TARIFF_URL = f"{BASE_URL}/v1/products/{PRODUCT_CODE}/electricity-tariffs/{TARIFF_CODE}"
RATE_URL = f"{TARIFF_URL}/standard-unit-rates/"
TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def get_rates():
    response = requests.get(RATE_URL)
    return json.loads(response.text)


def main():
    rate_data = get_rates()
    rates = [RateTimepoint(result) for result in rate_data['results']]
    for rate in rates:
        print(rate)


class RateTimepoint:
    def __init__(self, result):
        self.from_time = datetime.datetime.strptime(result['valid_from'], TIME_FORMAT)
        self.to_time = datetime.datetime.strptime(result['valid_to'], TIME_FORMAT)
        self.price_exc_vat = result['value_exc_vat']
        self.price_inc_vat = result['value_inc_vat']

    def __str__(self):
        return f"{self.from_time.strftime('%d/%m/%Y %H:%M')}-" \
               f"{self.from_time.strftime('%H:%M')}  £{self.price_inc_vat/100:.3f}"

    def __repr__(self):
        return str(self)


if __name__ == '__main__':
    main()
