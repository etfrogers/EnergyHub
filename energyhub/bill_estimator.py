from builtins import AttributeError
from collections import defaultdict
from datetime import datetime, timedelta, date, time, timezone
from functools import cached_property
from typing import Dict, Optional

import numpy as np

from energyhub.config import config
from energyhub.utils import day_start_end_times
from octopus_client.octopy.octopus_api import OctopusClient
from solaredge import SolarEdgeClient


def time_range(start: timedelta, stop: timedelta, step: timedelta):
    val = start
    while val < stop:
        yield val
        val += step


BILLING_PERIOD = timedelta(minutes=30)
BILLING_BOUNDARIES = list(zip(time_range(timedelta(0), timedelta(hours=24, minutes=0), BILLING_PERIOD),
                              time_range(BILLING_PERIOD, timedelta(hours=24, minutes=1), BILLING_PERIOD)))


def main():
    day = datetime(2023, 1, 21)
    start = day
    end = day + timedelta(days=1)
    tariff = OctopusClient(config.data['octopus']['region-code']).get_rates(start, end)
    print(tariff)
    est = BillEstimator()
    solar_estimate = est.estimate_consumption_from_solar_edge(day)
    print(solar_estimate)


class BillEstimate:
    def __init__(self):
        self._day: Optional[date] = None
        self._solar_edge_response = None
        self.consumption_response = None
        self.export_response = None

    @property
    def solar_edge_response(self):
        return self._solar_edge_response

    @solar_edge_response.setter
    def solar_edge_response(self, value):
        if self._solar_edge_response is not None:
            raise AttributeError('solar_edge_response can only bet set once')
        self._solar_edge_response = value

    @cached_property
    def billing_periods(self) -> np.ndarray:
        # current_tz = datetime.now(timezone.utc).astimezone().tzinfo
        day_start: datetime = datetime.combine(self.day, time(0))
        return np.array([
            tuple(day_start + b for b in bs)
            for bs in BILLING_BOUNDARIES
        ])

    @property
    def day(self):
        if self._day is None:
            raise AttributeError('day is not set')
        return self._day

    @day.setter
    def day(self, value: date):
        if self._day is None:
            self._day = value
        else:
            if self._day != value:
                raise ValueError('Day of a BillEstimate cannot be changed')

    @cached_property
    def consumption_estimate(self) -> np.ndarray:
        ts = self.solar_edge_response['timestamps']
        values = self.solar_edge_response['Purchased']
        return self._values_to_billing_periods(ts, values)

    @cached_property
    def export_estimate(self) -> np.ndarray:
        ts = self.solar_edge_response['timestamps']
        values = self.solar_edge_response['FeedIn']
        return self._values_to_billing_periods(ts, values)

    def _values_to_billing_periods(self, timestamps, values):
        if not len(timestamps) == len(values):
            raise AttributeError('Could not calculate consumption estimate: mismatched data sizes')
        periods = self.billing_periods
        estimate = np.zeros((periods.shape[0], ))
        for time_, val in zip(timestamps, values):
            index = np.logical_and(periods[:, 0] <= time_,
                                   time_ < periods[:, 1])
            assert len(np.where(index)) == 1
            estimate[index] += val
        return estimate

    @cached_property
    def consumption(self) -> np.ndarray:
        datapoints = self.consumption_response
        return self.meter_points_to_array(datapoints)

    @cached_property
    def export(self) -> np.ndarray:
        datapoints = self.export_response
        return self.meter_points_to_array(datapoints)

    def meter_points_to_array(self, datapoints):
        periods = self.billing_periods
        values = np.zeros_like(datapoints, dtype=float)
        for i, datapoint in enumerate(datapoints):
            # drop timezone info:assume same as local
            from_time = datapoint.from_time.replace(tzinfo=None)
            period_index = np.where(from_time == periods[:, 0])[0]
            assert period_index.size == 1
            assert datapoint.to_time.replace(tzinfo=None) == periods[period_index, 1]
            values[period_index] = datapoint.value
        return values


class BillEstimator:
    def __init__(self):
        self.solar_edge = SolarEdgeClient(config.data['solar-edge']['api-key'],
                                          config.data['solar-edge']['site-id'])
        oct_cf = config.data['octopus']
        oct = OctopusClient(region_code=oct_cf['region-code'],
                            api_key=oct_cf['api-key'],
                            export_mpan=oct_cf['export-mpan'],
                            export_serial=oct_cf['meter-serial'],
                            consumption_mpan=oct_cf['consumption-mpan'],
                            consumption_serial=oct_cf['meter-serial'],
                            )
        self.octopus = oct
        self._cache: Dict[date, BillEstimate] = defaultdict(lambda: BillEstimate())

    def _check_solar_edge(self, day: date):
        if self[day].solar_edge_response is None:
            details = self.solar_edge.get_energy_details(*day_start_end_times(day), 'QUARTER_OF_AN_HOUR')
            self[day].solar_edge_response = details

    def estimate_consumption_from_solar_edge(self, day: date) -> np.ndarray:
        self._check_solar_edge(day)
        return self[day].consumption_estimate

    def estimate_export_from_solar_edge(self, day: date) -> np.ndarray:
        self._check_solar_edge(day)
        return self[day].export_estimate


    def get_consumption_for_day(self, day: date) -> np.ndarray:
        datapoints = self.octopus.get_consumption_for_day(day)
        self[day].consumption_response = datapoints
        return self[day].consumption

    def get_export_for_day(self, day: date) -> np.ndarray:
        datapoints = self.octopus.get_export_for_day(day)
        self[day].export_response = datapoints
        return self[day].export

    def __getitem__(self, item: date) -> BillEstimate:
        estimate = self._cache[item]
        estimate.day = item
        return estimate


if __name__ == '__main__':
    main()
