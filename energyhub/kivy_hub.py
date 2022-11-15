'''
Application built from a  .kv file
==================================

This shows how to implicitly use a .kv file for your application. You
should see a full screen button labelled "Hello from test.kv".

After Kivy instantiates a subclass of App, it implicitly searches for a .kv
file. The file test.kv is selected because the name of the subclass of App is
TestApp, which implies that kivy should try to load "test.kv". That file
contains a root Widget.
'''
import textwrap
import time
from threading import Thread

import jlrpy
from kivy.app import App
from kivy.properties import NumericProperty, AliasProperty, StringProperty, BooleanProperty
from kivy.utils import platform
from kivy.clock import mainthread
import ssl
from contextlib import AbstractContextManager

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from ecoforest.ecoforest_processor import EcoforestClient
from solaredge.solar_edge_api import SolarEdgeClient
from energyhub.config import config
from mec.zp import MyEnergiHost
from kivy_arrow.arrow import Arrow

# kivy.require('1.0.7')

from kivy.core.window import Window
if platform != 'android':
    Window.size = (1440/5, 3216/5)


# noinspection PyUnresolvedReferences,PyProtectedMember
class NoSSLVerification(AbstractContextManager):
    def __enter__(self):
        self._original_context = ssl._create_default_https_context
        if platform == 'android':
            ssl._create_default_https_context = ssl._create_unverified_context

    def __exit__(self, exc_type, exc_val, exc_tb):
        ssl._create_default_https_context = self._original_context


class IconButton(ButtonBehavior, Image):
    pass


def list_to_dict(list_of_kv_pairs):
    return {v['key']: v['value'] for v in list_of_kv_pairs}


def km_to_miles(km):
    return 0.621371 * km


def popup_on_error(label: str):
    def decorator(function):
        def wrapper(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception as err:
                _warning(label + ' API Error', textwrap.fill(str(err), 37))
        return wrapper
    return decorator


def _warning(title: str, msg: str):
    Popup(title=title,
          content=Label(text=msg),
          size_hint=(0.95, 0.3)).open()


class EnergyHubApp(App):
    solar_production = NumericProperty(0)
    battery_production = NumericProperty(4)
    grid_power = NumericProperty(0)
    grid_exporting = BooleanProperty(False)
    battery_level = NumericProperty(0.5)
    battery_state = StringProperty('Charging')
    car_battery_level = NumericProperty(0.5)
    car_is_charging = BooleanProperty(False)
    car_range = NumericProperty(0.5)
    car_charge_rate_miles = NumericProperty(0.5)
    car_charge_rate_pc = NumericProperty(0.5)
    eddi_power = NumericProperty(0.5)
    zappi_power = NumericProperty(0.5)
    solar_edge_load = NumericProperty(0.5)
    heating_power = NumericProperty(0)
    dhw_power = NumericProperty(0)
    outside_temperature = NumericProperty(0)

    @property
    def small_size(self):
        return 25 if platform == 'android' else 15

    def _get_load_color(self):
        using_grid = self.grid_power > 0 and not self.grid_exporting
        generating_solar = self.solar_production > 0
        using_battery = self.battery_production > 0 and self.battery_state != 'Charging'
        eco_generation = generating_solar or using_battery
        if eco_generation and not using_grid:
            return 0, 0.8, 0, 1
        elif eco_generation:
            return 0.8, 0.8, 0, 1
        else:
            return 1, 0.5, 0, 1

    def __init__(self):
        super(EnergyHubApp, self).__init__()

        with NoSSLVerification():
            self.car_connection = jlrpy.Connection(config.data['jlr']['username'],
                                                   config.data['jlr']['password'])
            self.car_connection.refresh_tokens()

        self.my_energi_connection = MyEnergiHost(config.data['myenergi']['username'],
                                                 config.data['myenergi']['api-key'])

        self.solar_edge_connection = SolarEdgeClient(config.data['solar-edge']['api-key'],
                                                     config.data['solar-edge']['site-id'])
        self.ecoforest_connection = EcoforestClient(config.data['ecoforest']['server'],
                                                    config.data['ecoforest']['port'],
                                                    config.data['ecoforest']['serial-number'],
                                                    config.data['ecoforest']['auth-key'])

    def refresh(self):
        Thread(target=self._refresh_solar_edge).start()
        Thread(target=self._refresh_car).start()
        Thread(target=self._refresh_my_energi).start()
        Thread(target=self._refresh_heat_pump).start()

    @popup_on_error('MyEnergy')
    def _refresh_my_energi(self):
        with NoSSLVerification():
            self.my_energi_connection.refresh()
        self._update_my_energi_data()

    @mainthread
    def _update_my_energi_data(self):
        self.zappi_power = self.my_energi_connection.state.zappi_list()[0].charge_rate
        self.eddi_power = self.my_energi_connection.state.eddi_list()[0].charge_rate
        # TODO pstatus (connected)
        #   status (waiting for export)
        #   charge added

    def _jlr_vehicle_server_refresh(self, timeout=10, retry_time=1):
        vehicle = self.car_connection.vehicles[0]
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
    def _refresh_car(self):
        with NoSSLVerification():
            vehicle = self.car_connection.vehicles[0]
            self._jlr_vehicle_server_refresh()
            status = vehicle.get_status()  # This should get status from JLR servers to us
        self._update_car_status(status)

    @mainthread
    def _update_car_status(self, status):
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

    @popup_on_error('SolarEdge')
    def _refresh_solar_edge(self):
        power_flow_data = self.solar_edge_connection.get_power_flow()
        self._update_solar_edge_data(power_flow_data)

    @mainthread
    def _update_solar_edge_data(self, power_flow_data):
        if power_flow_data['unit'] == 'kW':
            conversion_factor = 1000
        else:
            raise NotImplementedError
        self.battery_production = power_flow_data['STORAGE']['currentPower'] * conversion_factor
        self.battery_level = power_flow_data['STORAGE']['chargeLevel']
        self.battery_state = power_flow_data['STORAGE']['status']
        self.solar_production = power_flow_data['PV']['currentPower'] * conversion_factor
        self.grid_power = power_flow_data['GRID']['currentPower'] * conversion_factor
        self.solar_edge_load = power_flow_data['LOAD']['currentPower'] * conversion_factor
        self.grid_exporting = {'from': 'LOAD', 'to': 'Grid'} in power_flow_data['connections']

    @popup_on_error('Ecoforest')
    def _refresh_heat_pump(self):
        status = self.ecoforest_connection.get_current_status()
        self._update_heat_pump_data(status)

    @mainthread
    def _update_heat_pump_data(self, status):
        self.heat_pump_power = status['ElectricalPower']['value']
        self.outside_temperature = status['OutsideTemp']['value']
        if status['DHWDemand']:
            self.dhw_power = self.heat_pump_power
            self.heating_power = 0
        elif status['HeatingDemand']:
            self.heating_power = self.heat_pump_power
            self.dhw_power = 0
        else:
            assert self.heat_pump_power == 0
            self.heating_power = 0
            self.dhw_power = 0

    def _get_battery_color(self):
        if self.battery_level > 80:
            return 0, 1, 0, 1
        elif self.battery_level > 40:
            return 1, .5, 0, 1
        else:
            return 1, 0, 0, 1

    def _get_remaining_load(self):
        return self.solar_edge_load - (self.zappi_power + self.eddi_power
                                       + self.heating_power + self.dhw_power)

    def _get_bottom_arms_power(self):
        return self.zappi_power + self.eddi_power + self.dhw_power

    def _get_car_charge_label(self):
        return (f'{self.car_battery_level} %'
                + (f' (+{self.car_charge_rate_pc if self.car_charge_rate_pc >= 0 else "?"} %/hr)'
                   if self.car_is_charging else '')
                + '\n'
                + f'{self.car_range:.0f} mi'
                + (f' (+{self.car_charge_rate_miles:.1f} mi/hr)' if self.car_is_charging else '')
                )

    battery_color = AliasProperty(
        _get_battery_color,
        bind=['battery_level']
    )
    remaining_load = AliasProperty(
        _get_remaining_load,
        bind=['solar_edge_load', 'zappi_power', 'eddi_power', 'heating_power', 'dhw_power']
    )
    car_charge_label = AliasProperty(
        _get_car_charge_label,
        bind=['car_battery_level', 'car_charge_rate_pc', 'car_is_charging',
              'car_range', 'car_charge_rate_miles']
    )
    _bottom_arms_power = AliasProperty(
        _get_bottom_arms_power,
        bind=['zappi_power', 'eddi_power', 'dhw_power']
    )
    load_color = AliasProperty(
        _get_load_color,
        bind=['solar_production', 'grid_exporting', 'grid_power', 'battery_production', 'battery_state']
    )

    @staticmethod
    def calculate_arrow_size(power):
        if power == 0:
            return 0
        else:
            size = (15 + (30 * power / 5000))
            if platform == 'android':
                size = (25 + (70 * power / 5000))
            return size


if __name__ == '__main__':
    app = EnergyHubApp()
    app.run()
