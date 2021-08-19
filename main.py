import datetime

from solaredgeoptimiser import yr_client
from solaredgeoptimiser.config import config, logger
from solaredgeoptimiser.solar_edge_api import get_power_flow


def main():
    forecast = yr_client.get_forecast(config['site-location'])
    coverage = yr_client.get_cloud_cover(forecast)
    logger.info(f'Average coverage from {datetime.datetime.now().__format__("%Y-%m-%d %H:%M:%S")} '
                f'until peak time ({config["peak-time"][0]}) is {coverage}')
    get_power_flow()


if __name__ == '__main__':
    main()
