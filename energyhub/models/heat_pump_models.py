from kivy.clock import mainthread
from kivy.properties import NumericProperty

from ecoforest.ecoforest_processor import EcoforestClient
from .model import BaseModel
from energyhub.utils import popup_on_error


class EcoforestModel(BaseModel):
    _heat_pump_power = NumericProperty(0)
    heating_power = NumericProperty(0)
    dhw_power = NumericProperty(0)
    outside_temperature = NumericProperty(0)

    def __init__(self, server, port, serial_number, auth_key, **kwargs):
        super().__init__(**kwargs)
        self.server = server
        self.port = port
        self.serial_number = serial_number
        self.auth_key = auth_key

    @popup_on_error('Error initialising Ecoforest')
    def _connect(self):
        self.connection = EcoforestClient(self.server, self.port, self.serial_number, self.auth_key)

    @popup_on_error('Ecoforest')
    def _refresh(self):
        status = self.connection.get_current_status()
        self.update_properties(status)

    @mainthread
    def _update_properties(self, status):
        self._heat_pump_power = status['ElectricalPower']['value']
        self.outside_temperature = status['OutsideTemp']['value']
        if status['DHWDemand']['value']:
            self.dhw_power = self._heat_pump_power
            self.heating_power = 0
        elif status['HeatingDemand']['value']:
            self.heating_power = self._heat_pump_power
            self.dhw_power = 0
        else:
            if self._heat_pump_power != 0:
                raise ValueError('Unknown heat pump demand signal')
            self.heating_power = 0
            self.dhw_power = 0
