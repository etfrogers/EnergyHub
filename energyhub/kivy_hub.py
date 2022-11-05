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
import ssl
from contextlib import AbstractContextManager

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image

import solaredge.solar_edge_api
from energyhub.config import config
from mec.zp import MyEnergiHost
from kivy_arrow.arrow import Arrow

# kivy.require('1.0.7')


class EnergyHubApp(App):
    solar_production = NumericProperty(0.5)
    battery_production = NumericProperty(4)
    grid_power = NumericProperty(0.5)
    battery_level = NumericProperty(0.5)
    battery_state = StringProperty('Charging')
    car_battery_level = NumericProperty(0.5)
    eddi_power = NumericProperty(0.5)
    zappi_power = NumericProperty(0.5)

    def __init__(self):
        super(EnergyHubApp, self).__init__()

        self.car_connection = jlrpy.Connection(config.data['jlr']['username'],
                                               config.data['jlr']['password'])
        self.car_connection.refresh_tokens()

        self.my_energi_connection = MyEnergiHost(config.data['myenergi']['username'],
                                                 config.data['myenergi']['api-key'])

    def refresh(self):
        power_flow_data = solaredge.solar_edge_api.get_power_flow()
        self.battery_production = power_flow_data['STORAGE']['currentPower']
        self.battery_level = power_flow_data['STORAGE']['chargeLevel']
        self.battery_state = power_flow_data['STORAGE']['status']
        self.solar_production = power_flow_data['PV']['currentPower']
        self.grid_power = power_flow_data['GRID']['currentPower']

        vehicle = self.car_connection.vehicles[0]
        self.car_battery_level = int(vehicle.get_status('EV_STATE_OF_CHARGE'))

        self.my_energi_connection.refresh()
        self.zappi_power = self.my_energi_connection.state.zappi_list()[0].charge_rate
        self.eddi_power = self.my_energi_connection.state.eddi_list()[0].charge_rate

    def _get_battery_color(self):
        if self.battery_level > 80:
            return 0, 1, 0, 1
        elif self.battery_level > 40:
            return 1, .5, 0, 1
        else:
            return 1, 0, 0, 1

    battery_color = AliasProperty(
        _get_battery_color,
        bind=['battery_level']
    )


if __name__ == '__main__':
    app = EnergyHubApp()
    app.run()
