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
from kivy.properties import NumericProperty

import solaredge.solar_edge_api
from energyhub.config import config


# kivy.require('1.0.7')


class EnergyHubApp(App):
    solar_production = NumericProperty(0.5)
    battery_production = NumericProperty(0.5)
    battery_level = NumericProperty(0.5)
    car_battery_level = NumericProperty(0.5)

    def __init__(self):
        super(EnergyHubApp, self).__init__()

        self.car_connection = jlrpy.Connection(config.data['jlr']['username'],
                                               config.data['jlr']['password'])
        self.car_connection.refresh_tokens()

    def on_solar_production(self, instance, value):
        self.root.ids.solar_prod_display.text = f'{value:.2f} kW'

    def on_battery_production(self, instance, value):
        self.root.ids.battery_prod_display.text = f'{value:.2f} kW'

    def on_battery_level(self, instance, value):
        self.root.ids.battery_level_display.text = f'{value:d} %'

    def on_car_battery_level(self, instance, value):
        self.root.ids.car_battery_level_display.text = f'{value:d} %'

    def refresh(self):
        power_flow_data = solaredge.solar_edge_api.get_power_flow()
        self.battery_production = power_flow_data['STORAGE']['currentPower']
        self.battery_level = power_flow_data['STORAGE']['chargeLevel']
        self.solar_production = power_flow_data['PV']['currentPower']

        vehicle = self.car_connection.vehicles[0]
        self.car_battery_level = int(vehicle.get_status('EV_STATE_OF_CHARGE'))


if __name__ == '__main__':
    app = EnergyHubApp()
    app.run()
