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

        data = self.connection.get_minute_data(serial, date.timetuple())
        timestamps, powers = history_dict_to_arrays(data)
        timestamps = timestamps.view(TimestampArray)
        return timestamps, powers


def history_dict_to_arrays(zappi_data: List[Dict]):
    timestamps = []
    import_power = []
    export_power = []
    charge_diverted = []
    charge_imported = []
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
        import_power.append(datapoint.get('imp', 0))
        export_power.append(datapoint.get('exp', 0))
        charge_diverted.append(datapoint.get('h1d', 0))
        charge_imported.append(datapoint.get('h1b', 0))
        volts.append(datapoint['v1'])
    timestamps = np.array(timestamps)
    import_power = np.array(import_power, dtype=float)
    export_power = np.array(export_power, dtype=float)
    charge_imported = np.array(charge_imported, dtype=float)
    charge_diverted = np.array(charge_diverted, dtype=float)
    volts = np.array(volts)/10
    to_watts = 4/volts
    import_power *= to_watts
    export_power *= to_watts
    charge_imported *= to_watts
    charge_diverted *= to_watts
    charging_power = charge_imported + charge_diverted
    powers = {'import': import_power,
              'export': export_power,
              'charge_diverted': charge_diverted,
              'charge_imported': charge_imported,
              'charging_power': charging_power,
              }
    return timestamps, powers
