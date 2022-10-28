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

import kivy
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import NumericProperty

# kivy.require('1.0.7')


class EnergyHubApp(App):
    solar_production = NumericProperty(0.5)

    def __init__(self):
        super(EnergyHubApp, self).__init__()

    def on_solar_production(self, instance, value):
        self.root.ids.solar_prod_display.text = f'{value/1000:.2f} kW'

    def refresh(self):
        self.solar_production += 400


if __name__ == '__main__':
    app = EnergyHubApp()

    def callback(dt):
        app.solar_production = 1230
    Clock.schedule_once(callback, 3)
    app.build()
    app.run()
