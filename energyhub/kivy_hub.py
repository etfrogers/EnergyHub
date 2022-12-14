from kivy.app import App
from kivy.clock import Clock
from kivy.properties import NumericProperty, AliasProperty, ObjectProperty
from kivy.utils import platform

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from matplotlib import pyplot as plt

# noinspection PyUnresolvedReferences
from kivy.garden.matplotlib import FigureCanvasKivyAgg

from energyhub.models.car_models import JLRCarModel
from energyhub.models.diverter_models import MyEnergiModel
from energyhub.models.heat_pump_models import EcoforestModel
from energyhub.models.solar_models import SolarEdgeModel
from energyhub.utils import popup_on_error, normalise_to_timestamps
from energyhub.config import config

# kivy.require('1.0.7')

from kivy.core.window import Window
if platform != 'android':
    Window.size = (1440/5, 3216/5)
    plt.rcParams['font.size'] = 12
else:
    plt.rcParams['font.size'] = 24


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

    def __init__(self, **kwargs):
        super(EnergyHubApp, self).__init__(**kwargs)
        self.solar_model = SolarEdgeModel(config.data['solar-edge']['api-key'],
                                          config.data['solar-edge']['site-id'])
        self.car_model = JLRCarModel(config.data['jlr']['username'],
                                     config.data['jlr']['password'],
                                     config.data['jlr'].get('vin', None))
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
        # build graphs needs to be called after initialisation to get sizes correct
        Clock.schedule_once(lambda x: self.build_history_graphs(), 0.1)

    def on_pause(self):
        return True

    def refresh(self):
        for model in self.models:
            model.refresh()

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
        history_panel = self.root.ids.history
        date_picker = self.root.ids.history.ids.history_date
        history_panel.ids.graph_panel.clear_widgets()
        if date is None:
            date = date_picker.date
        solar_timestamps, solar_data = self.solar_model.get_history_for_date(date)
        zappi_timestamps, zappi_powers = self.diverter_model.get_history_for_date(date, device='Z')
        eddi_timestamps, eddi_powers = self.diverter_model.get_history_for_date(date, device='E')
        heat_pump_timestamps, heat_pump_data = self.heat_pump_model.get_history_for_date(date)
        battery_timestamps, battery_data = self.solar_model.get_battery_history_for_date(date)
        production_power = solar_data['Production']
        load_power = solar_data['Consumption']
        export_power = solar_data['FeedIn']
        import_power = solar_data['Purchased']

        ref_timestamps = solar_timestamps
        car_charge_power = normalise_to_timestamps(ref_timestamps, zappi_timestamps, zappi_powers['total_power'])
        immersion_power = normalise_to_timestamps(ref_timestamps, eddi_timestamps, eddi_powers['total_power'])
        dhw_power = normalise_to_timestamps(ref_timestamps, heat_pump_timestamps, heat_pump_data['DHW_power'])
        heating_power = normalise_to_timestamps(ref_timestamps, heat_pump_timestamps, heat_pump_data['heating_power'])
        battery_grid_charging = normalise_to_timestamps(ref_timestamps, battery_timestamps,
                                                        battery_data['charge_power_from_grid'])
        battery_solar_charging = normalise_to_timestamps(ref_timestamps, battery_timestamps,
                                                         battery_data['charge_power_from_solar'])
        battery_discharging = normalise_to_timestamps(ref_timestamps, battery_timestamps,
                                                      battery_data['discharge_power'])
        battery_state = normalise_to_timestamps(ref_timestamps, battery_timestamps,
                                                battery_data['charge_percentage'])

        remaining_load = load_power - (car_charge_power + immersion_power
                                       + dhw_power + heating_power + battery_grid_charging)

        solar_production = production_power + battery_solar_charging - battery_discharging
        solar_consumption = solar_production - (export_power + battery_solar_charging)

        ref_hours = ref_timestamps.total_hours()
        self._plot_to_history_panel(ref_hours, (car_charge_power/1000,
                                                immersion_power/1000,
                                                dhw_power/1000,
                                                heating_power/1000,
                                                battery_grid_charging/1000,
                                                remaining_load/1000,
                                                ),
                                    labels=('Car charge', 'Immersion', 'DWH', 'Heating', 'Battery charging', 'Other'),
                                    )
        # plt.plot(ref_hours, load_power/1000, linestyle='--')

        self._plot_to_history_panel(ref_hours, (solar_consumption / 1000,
                                                battery_discharging / 1000,
                                                import_power / 1000,
                                                ),
                                    labels=('Solar consumption', 'Battery discharging', 'Import'),
                                    )
        # plt.plot(ref_hours, load_power/1000, linestyle='--')

        self._plot_to_history_panel(ref_hours, (solar_consumption/1000,
                                                battery_solar_charging/1000,
                                                export_power/1000
                                                ),
                                    labels=('Consumption', 'Battery charging', 'Export'),
                                    )

        ax = self._plot_to_history_panel(ref_hours, battery_state,
                                         # labels=('Battery state', ),
                                         plot_fun=plt.plot,
                                         )
        ax.set_ylim([0, 100])

    def _plot_to_history_panel(self, x, y, plot_fun=plt.stackplot, **kwargs):
        history_panel = self.root.ids.history.ids.graph_panel
        fig = plt.figure()
        plot_fun(x, y, **kwargs)
        plt.legend()
        plt.xticks([0, 6, 12, 18, 24])
        plt.tight_layout()
        widget = FigureCanvasKivyAgg(fig)
        widget.size_hint_y = None
        widget.height = self.root.width * 0.5
        history_panel.add_widget(widget)
        return plt.gca()


if __name__ == '__main__':
    app = EnergyHubApp()
    app.run()
