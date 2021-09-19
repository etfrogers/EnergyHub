import datetime
import logging

from solaredgeoptimiser import yr_client
from solaredgeoptimiser.config import config, LOG_TIME_FORMAT
from solaredgeoptimiser.solar_edge_settings import SolarEdgeConnection
from solaredgeoptimiser.solar_edge_api import get_power_flow, get_battery_level, BatteryNotFoundError

logger = logging.getLogger('solaredgeoptimiser.main')


def main():
    forecast = yr_client.get_forecast(config['site-location'])
    coverage = yr_client.get_cloud_cover(forecast)
    logger.info(f'Average coverage from {datetime.datetime.now().__format__(LOG_TIME_FORMAT)} '
                f'until peak time ({config["peak-time"][0]}) is {coverage}')
    get_power_flow()
    try:
        battery_charge = get_battery_level()
    except BatteryNotFoundError as err:
        logger.error(str(err) + ' - Stopping execution')
        return
    logger.info(f'Battery charge: {battery_charge}%')

    with SolarEdgeConnection() as se:
        power = se.get_current_generation_power()
    logger.info(f'Current power measured as {power} kW')


if __name__ == '__main__':
    # noinspection PyBroadException
    try:
        main()
    except Exception:
        logger.exception(str(Exception))
