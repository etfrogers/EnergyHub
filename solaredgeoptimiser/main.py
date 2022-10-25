import argparse
import datetime
import logging

from yrpy import yr_client
from energyhub.config import config, LOG_TIME_FORMAT
from solaredge.solar_edge_settings import SolarEdgeConnection
from solaredge.solar_edge_api import get_battery_level, BatteryNotFoundError

logger = logging.getLogger('solaredgeoptimiser.main')


def test():
    forecast = yr_client.get_forecast(config['site-location'])
    coverage = yr_client.get_cloud_cover(forecast)
    logger.info(f'Average coverage from {datetime.datetime.now().strftime(LOG_TIME_FORMAT)} '
                f'until peak time ({config["peak-time"][0]}) is {coverage}')
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


def main(args):
    check_for_clipped_charge(force=args.force)


def check_for_clipped_charge(interactive=True, force=False):
    logger.info('Starting check for clipped charge')
    start_of_collection_time = datetime.time(hour=10)
    start_of_peak_time = config['peak-time'][0]
    now = datetime.datetime.now()
    day_to_check = datetime.datetime.now().date()
    check_tomorrow = now.time() > start_of_peak_time
    if check_tomorrow:
        day_to_check += datetime.timedelta(days=1)
        check_message = 'Checking for clipped charge tomorrow: '
        battery_threshold = config['target_battery_level_evening']
    else:
        check_message = 'Checking for clipped charge today: '
        battery_threshold = config['min-morning-charge']

    logger.info(check_message + day_to_check.strftime('%d-%m-%Y') +
                f' (battery threshold: {battery_threshold}%)')
    forecast = yr_client.get_forecast(config['site-location'])
    start_time = datetime.datetime.combine(day_to_check, start_of_collection_time)
    end_time = datetime.datetime.combine(day_to_check, start_of_peak_time)
    avg_coverage, _ = yr_client.get_cloud_cover(forecast, start_time, end_time)
    logger.info(f'Average coverage from {start_time.strftime(LOG_TIME_FORMAT)} '
                f'until peak time ({end_time.strftime(LOG_TIME_FORMAT)}) is {avg_coverage:.1f}%')
    battery_charge = get_battery_level()
    logger.info(f'Current battery level {battery_charge:.1f}%')
    if battery_charge < battery_threshold:
        logger.info(f'Battery level of {battery_charge:.1f}% is less than '
                    f'{battery_threshold}%. Not switching to clipped charge')
    elif avg_coverage > 50 and not force:
        logger.info(f'Cloud coverage of {avg_coverage:.1f}% is greater than 50%. '
                    f'Not switching to clipped charge')
    else:
        if datetime.datetime.now().astimezone().utcoffset().seconds == 0:
            profile_name = 'Clipped charge 9-15'
        else:
            profile_name = 'Clipped charge'
        logger.info(f'Switching to "{profile_name}" for {day_to_check.strftime(LOG_TIME_FORMAT)}')
        with SolarEdgeConnection(interactive) as se:
            se.go_to_storage_profile()
            se.add_special_day(profile_name, day_to_check)


if __name__ == '__main__':
    # noinspection PyBroadException
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-f", "--force",
                            help="Switch on a clipped-charge day regardless of cloud coverage",
                            action="store_true")
        args = parser.parse_args()
        main(args)
    except Exception:
        logger.exception(str(Exception))
