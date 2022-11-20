import time

import jlrpy
from kivy.clock import mainthread
from kivy.properties import NumericProperty, BooleanProperty, AliasProperty

from .model import BaseModel
from energyhub.utils import popup_on_error, NoSSLVerification, list_to_dict, km_to_miles


class JLRCarModel(BaseModel):
    car_battery_level = NumericProperty(0.5)
    car_is_charging = BooleanProperty(False)
    car_range = NumericProperty(0.5)
    car_charge_rate_miles = NumericProperty(0.5)
    car_charge_rate_pc = NumericProperty(0.5)

    def __init__(self, username, password, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username = username
        self.password = password

    @popup_on_error('Error initialising JLR')
    def _connect(self):
        with NoSSLVerification():
            self.connection = jlrpy.Connection(self.username, self.password)
            self.connection.refresh_tokens()

    def _jlr_vehicle_server_refresh(self, timeout=10, retry_time=1):
        vehicle = self.connection.vehicles[0]
        response = vehicle.get_health_status()  # This should refresh status from the vehicle to JLR servers
        refresh_status = 'Started'
        elapsed_time = 0
        while refresh_status == 'Started' and elapsed_time < timeout:
            refresh_status = vehicle.get_service_status(response['customerServiceId'])['status']
            time.sleep(retry_time)
            elapsed_time += retry_time
        if refresh_status != 'Successful':
            raise ConnectionError('Could not refresh JLR vehicle')

    @popup_on_error('JLR')
    def _refresh(self):
        with NoSSLVerification():
            vehicle = self.connection.vehicles[0]
            self._jlr_vehicle_server_refresh()
            status = vehicle.get_status()  # This should get status from JLR servers to us
        self.update_properties(status)

    @mainthread
    def _update_properties(self, status):
        # alerts = status['vehicleAlerts']
        status = status['vehicleStatus']
        ev_status = list_to_dict(status['evStatus'])
        self.car_battery_level = int(ev_status['EV_STATE_OF_CHARGE'])
        self.car_is_charging = ev_status['EV_CHARGING_STATUS'] == 'CHARGING'
        car_range_in_km = float(ev_status['EV_RANGE_ON_BATTERY_KM'])
        self.car_range = km_to_miles(car_range_in_km)
        self.car_charge_rate_miles = km_to_miles(float(ev_status['EV_CHARGING_RATE_KM_PER_HOUR']))
        try:
            self.car_charge_rate_pc = float(ev_status['EV_CHARGING_RATE_SOC_PER_HOUR'])
        except ValueError:
            self.car_charge_rate_pc = -100

    def _get_charge_label(self):
        return (f'{self.car_battery_level} %'
                + (f' (+{self.car_charge_rate_pc if self.car_charge_rate_pc >= 0 else "?"} %/hr)'
                   if self.car_is_charging else '')
                + '\n'
                + f'{self.car_range:.0f} mi'
                + (f' (+{self.car_charge_rate_miles:.1f} mi/hr)' if self.car_is_charging else '')
                )

    charge_label = AliasProperty(
        _get_charge_label,
        bind=['car_battery_level', 'car_charge_rate_pc', 'car_is_charging',
              'car_range', 'car_charge_rate_miles']
    )
