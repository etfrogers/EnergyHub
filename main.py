import datetime

from solaredgeoptimiser import yr_client
from solaredgeoptimiser.config import config, logger


def main():
    forecast = yr_client.get_forecast(config['site-location'])
    coverage = yr_client.get_cloud_cover(forecast)
    logger.info(f'Average coverage from {datetime.datetime.now().__format__("%Y-%m-%d %H:%M:%S")} '
                f'until peak time ({config["peak-time"][0]}) is {coverage}')


if __name__ == '__main__':
    main()
