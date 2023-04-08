from builtins import AttributeError
from collections import defaultdict
from datetime import datetime, timedelta, date, time
from functools import cached_property, lru_cache
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


DATE_FORMAT = '%Y-%m-%d'
BILLING_PERIOD = timedelta(minutes=30)
BILLING_BOUNDARIES = list(zip(time_range(timedelta(0), timedelta(hours=24, minutes=0), BILLING_PERIOD),
                              time_range(BILLING_PERIOD, timedelta(hours=24, minutes=1), BILLING_PERIOD)))


class MeterReadingError(Exception):
    pass


class MissingMeterReadingError(MeterReadingError):
    pass


class DuplicateMeterReadingError(MeterReadingError):
    pass


class MeterReadingTimeMismatchError(MeterReadingError):
    pass


class BillEstimate:
    def __init__(self, octopus_client: OctopusClient, solaredge_client: SolarEdgeClient):
        self.octopus_client = octopus_client
        self.solar_edge_client = solaredge_client
        self._day: Optional[date] = None

    @cached_property
    def solar_edge_response(self):
        return self.solar_edge_client.get_energy_details(*day_start_end_times(self.day),
                                                         'QUARTER_OF_AN_HOUR')

    @cached_property
    def consumption_response(self):
        return self.octopus_client.get_consumption_for_day(self.day)

    @cached_property
    def export_response(self):
        return self.octopus_client.get_export_for_day(self.day)

    @cached_property
    def rate_response(self):
        return self.octopus_client.get_rates_for_day(self.day)

    @cached_property
    def export_rate_response(self):
        return self.octopus_client.get_export_rates_for_day(self.day)

    @cached_property
    def billing_periods(self) -> np.ndarray:
        day_start: datetime = datetime.combine(self.day, time(0), tzinfo=config.timezone)
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
        # Note that Solar Edge returns Wh, and we convert to kWh
        return self._values_to_billing_periods(ts, values) / 1000

    @cached_property
    def export_estimate(self) -> np.ndarray:
        ts = self.solar_edge_response['timestamps']
        values = self.solar_edge_response['FeedIn']
        # Note that Solar Edge returns Wh, and we convert to kWh
        return self._values_to_billing_periods(ts, values) / 1000

    def estimated_bill(self, inc_vat: bool = True) -> float:
        # noinspection PyTypeChecker
        return np.sum(self.estimated_itemised_bill(inc_vat))

    def calculated_bill(self, inc_vat: bool = True) -> float:
        # noinspection PyTypeChecker
        return np.sum(self.calculated_itemised_bill(inc_vat))

    def estimated_itemised_bill(self, inc_vat: bool = True) -> np.ndarray:
        return self.rates(inc_vat) * self.consumption_estimate

    def calculated_itemised_bill(self, inc_vat: bool = True) -> np.ndarray:
        return self.rates(inc_vat) * self.consumption

    def estimated_credit(self, inc_vat: bool = True) -> float:
        # noinspection PyTypeChecker
        return np.sum(self.estimated_itemised_credit(inc_vat))

    def calculated_credit(self, inc_vat: bool = True) -> float:
        # noinspection PyTypeChecker
        return np.sum(self.calculated_itemised_credit(inc_vat))

    def estimated_itemised_credit(self, inc_vat: bool = True) -> np.ndarray:
        return self.export_rates(inc_vat) * self.export_estimate

    def calculated_itemised_credit(self, inc_vat: bool = True) -> np.ndarray:
        return self.export_rates(inc_vat) * self.export

    @lru_cache
    def rates(self, inc_vat: bool = True) -> np.ndarray:
        datapoints = self.rate_response
        var_name = 'price_inc_vat' if inc_vat else 'price_exc_vat'
        return self.meter_points_to_array(datapoints, var_name)

    @lru_cache
    def export_rates(self, inc_vat: bool = True) -> np.ndarray:
        datapoints = self.export_rate_response
        var_name = 'price_inc_vat' if inc_vat else 'price_exc_vat'
        return self.meter_points_to_array(datapoints, var_name)

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
        data = self.meter_points_to_array(datapoints)
        if data.size == 0:
            raise MissingMeterReadingError(f'No consumption readings found for {self.day.strftime(DATE_FORMAT)}')
        return data

    @cached_property
    def export(self) -> np.ndarray:
        datapoints = self.export_response
        data = self.meter_points_to_array(datapoints)
        if data.size == 0:
            raise MissingMeterReadingError(f'No export readings found for {self.day.strftime(DATE_FORMAT)}')
        return data

    def meter_points_to_array(self, datapoints, value_name: str = 'value'):
        periods = self.billing_periods
        values = np.zeros_like(datapoints, dtype=float)
        for i, datapoint in enumerate(datapoints):
            period_index = np.where(datapoint.from_time == periods[:, 0])[0]
            if period_index.size == 0:
                raise MissingMeterReadingError
            elif period_index.size > 1:
                raise DuplicateMeterReadingError
            if datapoint.to_time != periods[period_index, 1]:
                raise MeterReadingTimeMismatchError
            values[period_index] = getattr(datapoint, value_name)
        return values


class BillEstimator:
    def __init__(self):
        self.solar_edge = SolarEdgeClient(config.data['solar-edge']['api-key'],
                                          config.data['solar-edge']['site-id'],
                                          timezone=config.timezone)
        oct_cf = config.data['octopus']
        oct = OctopusClient(region_code=oct_cf['region-code'],
                            api_key=oct_cf['api-key'],
                            export_mpan=oct_cf['export-mpan'],
                            export_serial=oct_cf['meter-serial'],
                            consumption_mpan=oct_cf['consumption-mpan'],
                            consumption_serial=oct_cf['meter-serial'],
                            )
        self.octopus = oct
        self._cache: Dict[date, BillEstimate] = defaultdict(lambda: BillEstimate(self.octopus, self.solar_edge))

    def estimate_consumption_from_solar_edge(self, day: date) -> np.ndarray:
        return self[day].consumption_estimate

    def estimate_export_from_solar_edge(self, day: date) -> np.ndarray:
        return self[day].export_estimate

    def get_consumption_for_day(self, day: date) -> np.ndarray:
        return self[day].consumption

    def get_export_for_day(self, day: date) -> np.ndarray:
        return self[day].export

    def calculate_bill_for_day(self, day: date, inc_vat: bool):
        return self[day].calculated_bill(inc_vat)

    def estimate_bill_for_day(self, day: date, inc_vat: bool):
        return self[day].estimated_bill(inc_vat)

    def calculate_credit_for_day(self, day: date, inc_vat: bool):
        return self[day].calculated_credit(inc_vat)

    def estimate_credit_for_day(self, day: date, inc_vat: bool):
        return self[day].estimated_credit(inc_vat)


    def __getitem__(self, item: date) -> BillEstimate:
        estimate = self._cache[item]
        estimate.day = item
        return estimate
