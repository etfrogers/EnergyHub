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
import jlrpy
from kivy.app import App
from kivy.properties import NumericProperty, AliasProperty, StringProperty
from kivy.utils import platform
import ssl
from contextlib import AbstractContextManager

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup

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


class EnergyHubApp(App):
    solar_production = NumericProperty(0.5)
    battery_production = NumericProperty(4)
    grid_power = NumericProperty(0)
    battery_level = NumericProperty(0.5)
    battery_state = StringProperty('Charging')
    car_battery_level = NumericProperty(0.5)
    eddi_power = NumericProperty(0.5)
    zappi_power = NumericProperty(0.5)
    solar_edge_load = NumericProperty(0.5)
    heat_pump_power = NumericProperty(0)

    @property
    def small_size(self):
        return 25 if platform == 'android' else 15

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

    def refresh(self):
        try:
            self._refresh_solar_edge()
        except Exception as err:
            self._warning('SolarEdge API Error', str(err))

        try:
            self._refresh_car()
        except Exception as err:
            self._warning('JLR API Error', str(err))

        try:
            self._refresh_my_energi()
        except Exception as err:
            self._warning('MyEnergy API Error', str(err))

    @staticmethod
    def _warning(title, msg):
        Popup(title=title,
              content=Label(text=msg),
              size_hint=(0.8, 0.2)).open()

    def _refresh_my_energi(self):
        with NoSSLVerification():
            self.my_energi_connection.refresh()
        self.zappi_power = self.my_energi_connection.state.zappi_list()[0].charge_rate / 1000
        self.eddi_power = self.my_energi_connection.state.eddi_list()[0].charge_rate / 1000
        # TODO pstatus (connected)
        #   status (waiting for export)
        #   charge added

    def _refresh_car(self):
        with NoSSLVerification():
            vehicle = self.car_connection.vehicles[0]
            self.car_battery_level = int(vehicle.get_status('EV_STATE_OF_CHARGE'))

    def _refresh_solar_edge(self):
        power_flow_data = self.solar_edge_connection.get_power_flow()
        self.battery_production = power_flow_data['STORAGE']['currentPower']
        self.battery_level = power_flow_data['STORAGE']['chargeLevel']
        self.battery_state = power_flow_data['STORAGE']['status']
        self.solar_production = power_flow_data['PV']['currentPower']
        self.grid_power = power_flow_data['GRID']['currentPower']
        self.solar_edge_load = power_flow_data['LOAD']['currentPower']

    def _get_battery_color(self):
        if self.battery_level > 80:
            return 0, 1, 0, 1
        elif self.battery_level > 40:
            return 1, .5, 0, 1
        else:
            return 1, 0, 0, 1

    def _get_remaining_load(self):
        return self.solar_edge_load - (self.zappi_power + self.eddi_power + self.heat_pump_power)

    battery_color = AliasProperty(
        _get_battery_color,
        bind=['battery_level']
    )
    remaining_load = AliasProperty(
        _get_remaining_load,
        bind=['solar_edge_load', 'zappi_power', 'eddi_power', 'heat_pump_power']
    )

    @staticmethod
    def calculate_arrow_size(power):
        return 10 + (30 * power / 5)


if __name__ == '__main__':
    app = EnergyHubApp()
    app.run()
