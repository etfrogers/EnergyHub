import datetime
from typing import List, Dict

import numpy as np
from kivy.clock import mainthread
from kivy.properties import NumericProperty

from energyhub.models.model import BaseModel
from energyhub.utils import popup_on_error, NoSSLVerification, TimestampArray
from mec.zp import MyEnergiHost


class MyEnergiModel(BaseModel):
    immersion_power = NumericProperty(0)
    car_charger_power = NumericProperty(0)

    def __init__(self, username, api_key, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.api_key = api_key

    @popup_on_error('Error initialising MyEnergi')
    def _connect(self):
        self.connection = MyEnergiHost(self.username, self.api_key)

    @popup_on_error('MyEnergi')
    def _refresh(self):
        with NoSSLVerification():
            self.connection.refresh()
        self.update_properties()

    @mainthread
    def _update_properties(self, data):
        self.car_charger_power = self.zappi.charge_rate
        self.immersion_power = self.eddi.charge_rate
        # TODO pstatus (connected)
        #   status (waiting for export)
        #   charge added

    @property
    def zappi(self):
        if self.connection.state is None and self.thread:
            self.thread.join()
        return self.connection.state.zappi_list()[0]

    @property
    def eddi(self):
        if self.connection.state is None and self.thread:
            self.thread.join()
        return self.connection.state.eddi_list()[0]

    def get_history_for_date(self, date: datetime.date,
                             device: str = 'Z') -> (np.ndarray, Dict[str, np.ndarray]):
        if device == 'Z':
            serial = self.zappi.sno
        elif device == 'E':
            serial = self.eddi.sno
        else:
            raise ValueError("Device must be 'E' or 'Z'")

        with NoSSLVerification():
            data = self.connection.get_minute_data(serial, date.timetuple())
        timestamps, powers = history_dict_to_arrays(data)
        mean_voltage_per_hour = {hour: np.mean([d['v1'] for d in data if d.get('hr', 0) == hour]) for hour in range(24)}
        hour_data = self.connection.get_hour_data(serial, date.timetuple())
        energies = hour_dict_to_energies(hour_data, mean_voltage_per_hour)
        timestamps = timestamps.view(TimestampArray)
        output = powers
        output.update(energies)
        return timestamps, output


MY_ENERGI_NAME_MAPPING = {
    'import': 'imp',
    'export': 'exp',
    'diverted': 'h1d',
    'imported': 'h1b',
}


def hour_dict_to_energies(hour_data: List[Dict], mean_voltage_per_hour: Dict):
    energies = {}
    for name, myenergi_name in MY_ENERGI_NAME_MAPPING.items():
        energies[name + '_energy'] = sum([datapoint.get(myenergi_name, 0)
                                          / (60*60)
                                          # / mean_voltage_per_hour[datapoint.get('hr', 0)]
                                          for datapoint in hour_data])
    energies['total_energy'] = energies['diverted_energy'] + energies['imported_energy']
    return energies


def history_dict_to_arrays(zappi_data: List[Dict]):
    timestamps = []
    powers = {}
    for name in MY_ENERGI_NAME_MAPPING:
        powers[name] = []
    volts = []
    for datapoint in zappi_data:
        # entries with zero value are omitted from data
        timestamp = datetime.datetime(year=datapoint['yr'],
                                      month=datapoint['mon'],
                                      day=datapoint['dom'],
                                      hour=datapoint.get('hr', 0),  # hr may not be present
                                      minute=datapoint.get('min', 0),  # min may not be present
                                      )
        timestamps.append(timestamp)
        volts.append(datapoint['v1'])
        for name, myenergi_name in MY_ENERGI_NAME_MAPPING.items():
            powers[name].append(datapoint.get(myenergi_name, 0))
    timestamps = np.array(timestamps)
    for name in MY_ENERGI_NAME_MAPPING:
        powers[name] = np.array(powers[name], dtype=float)
    volts = np.array(volts)/10
    to_watts = 4/volts
    for name in MY_ENERGI_NAME_MAPPING:
        powers[name] *= to_watts
    powers['total'] = powers['diverted'] + powers['imported']
    for name in list(powers):
        powers[name + '_power'] = powers.pop(name)
    return timestamps, powers
