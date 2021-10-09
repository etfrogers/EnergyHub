import datetime
import logging

from solaredgeoptimiser import yr_client
from solaredgeoptimiser.config import config, LOG_TIME_FORMAT
from solaredgeoptimiser.solar_edge_settings import SolarEdgeConnection
from solaredgeoptimiser.solar_edge_api import get_power_flow, get_battery_level, BatteryNotFoundError
from solaredgeoptimiser.yr_client import get_sunrise_sunset

logger = logging.getLogger('solaredgeoptimiser.main')


def test():
    forecast = yr_client.get_forecast(config['site-location'])
    coverage = yr_client.get_cloud_cover(forecast)
    logger.info(f'Average coverage from {datetime.datetime.now().strftime(LOG_TIME_FORMAT)} '
                f'until peak time ({config["peak-time"][0]}) is {coverage}')
    # get_power_flow()
    try:
        battery_charge = get_battery_level()
    except BatteryNotFoundError as err:
        logger.error(str(err) + ' - Stopping execution')
        return
    logger.info(f'Battery charge: {battery_charge}%')

    with SolarEdgeConnection() as se:
        se.go_to_storage_profile()
        se.add_special_day('Maximise SC', datetime.date(year=2021, month=12, day=31))
    # logger.info(f'Current power measured as {power} kW')


def main():
    check_for_clipped_charge()
    # get_sunrise_sunset(config['site-location'])


def check_for_clipped_charge():
    start_of_collection_time = datetime.time(hour=10)
    now = datetime.datetime.now()
    day_to_check = datetime.datetime.now().date()
    check_tomorrow = now.time() > start_of_collection_time
    if check_tomorrow:
        day_to_check += datetime.timedelta(days=1)
        check_message = 'Checking for clipped charge tomorrow: '
        battery_threshold = config['min-morning-charge']
    else:
        check_message = 'Checking for clipped charge today: '
        battery_threshold = config['target_battery_level_evening']

    logger.debug(check_message + day_to_check.strftime('%d-%m-%Y') +
                 f' (battery threshold: {battery_threshold}%)')
    forecast = yr_client.get_forecast(config['site-location'])
    start_time = datetime.datetime.combine(day_to_check, start_of_collection_time)
    start_of_peak_time = config['peak-time'][0]
    end_time = datetime.datetime.combine(day_to_check, start_of_peak_time)
    avg_coverage, _ = yr_client.get_cloud_cover(forecast, start_time, end_time)
    logger.info(f'Average coverage from {start_time.strftime(LOG_TIME_FORMAT)} '
                f'until peak time ({end_time.strftime(LOG_TIME_FORMAT)}) is {avg_coverage}')
    battery_charge = get_battery_level()

    if battery_charge < battery_threshold:
        logger.info(f'Battery level of {battery_charge}% is less than '
                    f'{battery_threshold}%. Not switching to clipped charge')
    elif avg_coverage > 50:
        logger.info(f'Cloud coverage of {avg_coverage} is greater than 50%. '
                    f'Not switching to clipped charge')
    else:
        logger.info(f'Switching to clipped charge for {day_to_check.strftime(LOG_TIME_FORMAT)}')
        with SolarEdgeConnection() as se:
            se.go_to_storage_profile()
            se.add_special_day('Clipped charge', day_to_check)


if __name__ == '__main__':
    # noinspection PyBroadException
    try:
        main()
    except Exception:
        logger.exception(str(Exception))
