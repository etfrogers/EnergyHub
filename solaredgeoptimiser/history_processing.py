import datetime
import functools
import json
import re
from functools import cached_property, partialmethod
from glob import glob
from typing import Tuple, List

import numpy as np
import matplotlib.pyplot as plt

from solaredgeoptimiser.solar_edge_api import get_power_history_for_site, API_TIME_FORMAT


# noinspection PyUnresolvedReferences
class PowerHistory:
    meters = ['consumption', 'production', 'feed_in', 'purchased', 'self_consumption']

    def __init__(self):
        self._timestamp_list = []
        for meter in self.meters:
            setattr(self, self._list_name(meter), [])
        self.load_power_history()

    def load_power_history(self, get_from_server: bool = False) -> None:
        if get_from_server:
            get_power_history_for_site()
        history_files = glob('power_details_*.json')
        for filename in history_files:
            with open(filename) as file:
                file_data = json.load(file)
            details = file_data['powerDetails']
            assert details['timeUnit'] == 'QUARTER_OF_AN_HOUR'
            assert details['unit'] == 'W'
            timestamp_list = self._extract_time_stamps(details['meters'][0]['values'])
            self._timestamp_list.extend(timestamp_list)
            for meter_data in details['meters']:
                meter_name = meter_data['type']
                values = meter_data['values']
                assert self._extract_time_stamps(values) == timestamp_list
                powers = [entry.get('value', 0) for entry in values]
                list_ = self._get_list(meter_name)
                list_.extend(powers)

        indices = argsort(self._timestamp_list)
        self._timestamp_list = list_indexed_by_list(self._timestamp_list, indices)
        for list_ in self._meter_list_names():
            sorted_list = list_indexed_by_list(getattr(self, list_), indices)
            setattr(self, list_, sorted_list)

    @property
    def timestamps(self):
        return np.array(self._timestamp_list)

    @staticmethod
    def _extract_time_stamps(value_list):
        times = [datetime.datetime.strptime(entry['date'], API_TIME_FORMAT) for entry in value_list]
        return times

    def _list_to_array(self, meter: str):
        return np.array(getattr(self, self._list_name(meter)))

    def _meter_list_names(self):
        for meter in self.meters:
            yield self._list_name(meter)

    @staticmethod
    def _list_name(meter_name: str):
        return f'_{_camel_to_snake(meter_name)}_list'

    def _get_list(self, meter_name) -> List:
        return getattr(self, self._list_name(meter_name))

    def plot_production(self):
        time = datetime.datetime(2021, 7, 9)

        plt.figure()
        ax1 = plt.subplot(2, 1, 1)
        plt.plot(self.timestamps, self.production, label='Production')
        plt.plot(self.timestamps, self.feed_in, label='Export')
        plt.plot(self.timestamps, self.purchased, label='Import')
        ax1.set_xlim([time, time + datetime.timedelta(days=1)])
        plt.legend()

        ax2 = plt.subplot(2, 1, 2)
        plt.plot(self.timestamps, self.consumption, label='Consumption')
        plt.plot(self.timestamps, self.self_consumption, label='Self Consumption')
        plt.legend()
        ax2.set_xlim([time, time + datetime.timedelta(days=1)])

        plt.show()


for meter_ in PowerHistory.meters:
    # noinspection PyProtectedMember
    setattr(PowerHistory, meter_, property(fget=functools.partial(PowerHistory._list_to_array, meter=meter_)))


def _camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def argsort(seq):
    # http://stackoverflow.com/questions/3071415/efficient-method-to-calculate-the-rank-vector-of-a-list-in-python
    return sorted(range(len(seq)), key=seq.__getitem__)


def list_indexed_by_list(lst: List, indices: List[int]) -> List:
    return [lst[i] for i in indices]


def main():
    history = PowerHistory()
    history.plot_production()


if __name__ == '__main__':
    main()
