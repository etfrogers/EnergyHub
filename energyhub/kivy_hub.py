import datetime
import time

from kivy.app import App
from kivy.properties import NumericProperty, AliasProperty, ObjectProperty
from kivy.utils import platform

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from matplotlib import pyplot as plt

import numpy as np
from kivy.garden.matplotlib import FigureCanvasKivyAgg

from energyhub.models.car_models import JLRCarModel
from energyhub.models.diverter_models import MyEnergiModel
from energyhub.models.heat_pump_models import EcoforestModel
from energyhub.models.solar_models import SolarEdgeModel
from energyhub.utils import popup_on_error, timestamps_to_hours
from energyhub.config import config

# kivy.require('1.0.7')

from kivy.core.window import Window
if platform != 'android':
    Window.size = (1440/5, 3216/5)


# TODO swipe down to refresh
# TODO history tab
# TODO planning tab
# TODO House icon
# TODO Nest integration
# TODO Heat pump COP - inst
# TODO DHW bug?


class IconButton(ButtonBehavior, Image):
    pass


class EnergyHubApp(App):
    solar_model = ObjectProperty()
    car_model = ObjectProperty()
    heat_pump_model = ObjectProperty()
    diverter_model = ObjectProperty()
    _solar_edge_load = NumericProperty(0)
    _heating_power = NumericProperty(0)
    _dhw_power = NumericProperty(0)
    _car_charger_power = NumericProperty(0)
    _immersion_power = NumericProperty(0)

    @property
    def small_size(self):
        return 25 if platform == 'android' else 15

    def __init__(self, *args, **kwargs):
        super(EnergyHubApp, self).__init__(**kwargs)
        self.solar_model = SolarEdgeModel(config.data['solar-edge']['api-key'],
                                          config.data['solar-edge']['site-id'])
        self.car_model = JLRCarModel(config.data['jlr']['username'],
                                     config.data['jlr']['password'])
        self.heat_pump_model = EcoforestModel(config.data['ecoforest']['server'],
                                              config.data['ecoforest']['port'],
                                              config.data['ecoforest']['serial-number'],
                                              config.data['ecoforest']['auth-key'])
        self.diverter_model = MyEnergiModel(config.data['myenergi']['username'],
                                            config.data['myenergi']['api-key'])

        self.solar_model.bind(load=self.setter('_solar_edge_load'))
        self.heat_pump_model.bind(heating_power=self.setter('_heating_power'))
        self.heat_pump_model.bind(dhw_power=self.setter('_dhw_power'))
        self.diverter_model.bind(immersion_power=self.setter('_immersion_power'))
        self.diverter_model.bind(car_charger_power=self.setter('_car_charger_power'))

    @property
    def models(self):
        return [self.solar_model, self.car_model, self.heat_pump_model, self.diverter_model]

    def build(self):
        super(EnergyHubApp, self).build()
        for model in self.models:
            model.connect()
        for model in self.models:
            model.thread.join()
        self.refresh()

    def on_pause(self):
        return True

    def refresh(self):
        for model in self.models:
            model.refresh()
        self.build_history_graphs()

    def _get_remaining_load(self):
        return self.solar_model.load - (self.diverter_model.immersion_power
                                        + self.diverter_model.car_charger_power
                                        + self.heat_pump_model.heating_power
                                        + self.heat_pump_model.dhw_power)

    def _get_bottom_arms_power(self):
        return (self.diverter_model.car_charger_power
                + self.diverter_model.immersion_power
                + self.heat_pump_model.dhw_power)

    remaining_load = AliasProperty(
        _get_remaining_load,
        bind=['_solar_edge_load', '_car_charger_power', '_immersion_power', '_heating_power', '_dhw_power']
    )
    _bottom_arms_power = AliasProperty(
        _get_bottom_arms_power,
        bind=['_car_charger_power', '_immersion_power', '_dhw_power']
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

    @popup_on_error('History')
    def build_history_graphs(self, date=None):
        return
        history_panel = self.root.ids.history
        date_picker = history_panel.ids.history_date
        history_panel.clear_widgets()
        history_panel.add_widget(date_picker)
        if date is None:
            date = date_picker.date
        data = self.solar_model.connection.get_power_history_for_day(date)
        times = data['timestamps']
        production_power = data['Production']
        load_power = data['Consumption']
        export_power = data['FeedIn']
        import_power = data['Purchased']

        try:
            zappi_serial = self.zappi.sno
            eddi_serial = self.eddi.sno
        except TypeError:
            time.sleep(1)
            zappi_serial = self.zappi.sno
            eddi_serial = self.eddi.sno

        zappi_data = self.my_energi_connection.get_minute_data(zappi_serial, date.timetuple())
        eddi_data = self.my_energi_connection.get_minute_data(eddi_serial, date.timetuple())
        zappi_timestamps, zappi_powers = zappi_dict_to_arrays(zappi_data)
        eddi_timestamps, eddi_powers = zappi_dict_to_arrays(eddi_data)

        hours = timestamps_to_hours(times)
        fig = plt.figure()
        plt.plot(hours, production_power/1000)
        plt.plot(hours, load_power/1000)
        plt.plot(hours, export_power/1000)
        plt.plot(hours, import_power/1000)
        plt.xticks([0, 6, 12, 18, 24])
        plt.ylabel('Power (kW)')

        # adding plot to kivy boxlayout
        history_panel.add_widget(FigureCanvasKivyAgg(fig))

        fig = plt.figure()
        plt.plot(timestamps_to_hours(zappi_timestamps), np.array([p / 1000 for p in zappi_powers.values()]).T)
        plt.xticks([0, 6, 12, 18, 24])
        history_panel.add_widget(FigureCanvasKivyAgg(fig))

        fig = plt.figure()
        plt.plot(timestamps_to_hours(eddi_timestamps), np.array([p / 1000 for p in eddi_powers.values()]).T)
        plt.xticks([0, 6, 12, 18, 24])
        history_panel.add_widget(FigureCanvasKivyAgg(fig))


if __name__ == '__main__':
    app = EnergyHubApp()
    app.run()
