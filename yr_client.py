import json
from datetime import datetime
from urllib.parse import urljoin

import requests

from config import config


YR_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
YR_API_URL = 'https://api.met.no/weatherapi/locationforecast/2.0/'
PROJECT_ID = 'https://github.com/etfrogers/SolarEdge'


def get_forecast(location: dict, forecast_style: str = 'compact'):
    user_agent = {'User-agent': PROJECT_ID}
    # forecast_style = 'compact'
    url = urljoin(YR_API_URL, forecast_style)
    response = requests.get(url, headers=user_agent, params=location)
    response.raise_for_status()
    return json.loads(response.text)


def get_cloud_cover(forecast: dict):
    for timepoint in forecast['properties']['timeseries']:
        time = datetime.strptime(timepoint["time"], YR_TIME_FORMAT)
        cloud_cover = timepoint["data"]["instant"]["details"]["cloud_area_fraction"]
        print(f'{time}: cloud cover {cloud_cover}%')


if __name__ == '__main__':
    forecast = get_forecast(config['site-location'])
    get_cloud_cover(forecast)
