from threading import Thread

import numpy as np
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.utils import platform

from matplotlib import pyplot as plt
from adjustText import adjust_text

# noinspection PyUnresolvedReferences
from kivy.garden.matplotlib import FigureCanvasKivyAgg

from ecoforest.plotting import stacked_bar
from energyhub.models.car_models import JLRCarModel
from energyhub.models.diverter_models import MyEnergiModel
from energyhub.models.heat_pump_models import EcoforestModel
from energyhub.models.model_set import ModelSet
from energyhub.models.solar_models import SolarEdgeModel
from energyhub.utils import popup_on_error, normalise_to_timestamps
from energyhub.config import config

# kivy.require('1.0.7')

from kivy.core.window import Window
if platform != 'android':
    Window.size = (1440/4, 3216/4)
    plt.rcParams['font.size'] = 8
else:
    plt.rcParams['font.size'] = 24


# TODO
#   refresh clock
#   refresh on resume
#   more current status
# TODO save state?
# TODO caching of myenergi/solar_edge history
# TODO handle errors on connection
# TODO fix history bugs on 29/12, 26/12
# TODO settings
# TODO Fix tab strip width
# TODO planning tab
#   weather icons
#   boost by time, kWh, miles
#   Days car will be out, and distance
#   Notification of low prices
#   Plotting of prices
# TODO House icon
# TODO Nest integration
# TODO Heat pump COP - inst ++
# TODO Car status indication
# TODO kivy logging


class EnergyHubApp(App):

    def __init__(self, **kwargs):
        super(EnergyHubApp, self).__init__(**kwargs)
        self._refreshing = False
        self._refreshing_history = False
        solar_model = SolarEdgeModel(config.data['solar-edge']['api-key'],
                                          config.data['solar-edge']['site-id'],
                                          config.timezone)
        car_model = JLRCarModel(config.data['jlr']['username'],
                                     config.data['jlr']['password'],
                                     config.data['jlr'].get('vin', None))
        heat_pump_model = EcoforestModel(config.data['ecoforest']['server'],
                                              config.data['ecoforest']['port'],
                                              config.data['ecoforest']['serial-number'],
                                              config.data['ecoforest']['auth-key'],
                                              timezone=config.timezone)
        diverter_model = MyEnergiModel(config.data['myenergi']['username'],
                                            config.data['myenergi']['api-key'],
                                            config.timezone)
        self.models = ModelSet(solar=solar_model,
                               car=car_model,
                               heat_pump=heat_pump_model,
                               diverter=diverter_model)

    def build(self):
        super(EnergyHubApp, self).build()
        for model in self.models:
            model.connect()
        for model in self.models:
            model.get_result('connect')
        self.root.ids.current_status.refresh()
        # build graphs needs to be called after initialisation to get sizes correct
        Clock.schedule_once(lambda x: Thread(self.build_history_graphs()).start(), 0.1)

    def on_pause(self):
        return True

    def check_pull_refresh_history(self, view):
        if view.scroll_y <= 1.1 or self._refreshing_history:
            return
        self.build_history_graphs()

    def _end_refreshing_history(self):
        self._refreshing_history = False

    @popup_on_error('History fetching', _end_refreshing_history)
    def build_history_graphs(self, date=None):
        self._refreshing_history = True
        history_panel = self.root.ids.history
        date_picker = self.root.ids.history.ids.history_date
        graph_panel = history_panel.ids.graph_panel
        for graph_widget in graph_panel.children:
            plt.close(graph_widget.figure)
        graph_panel.clear_widgets()
        if date is None:
            date = date_picker.date
        self.models.solar.get_history_for_date(date)
        self.models.solar.get_battery_history_for_date(date)
        self.models.diverter.get_history_for_date(date, 'Z')
        self.models.diverter.get_history_for_date(date, 'E')
        self.models.heat_pump.get_history_for_date(date)

        solar_timestamps, solar_data = self.models.solar.get_result('get_history_for_date', date)
        zappi_timestamps, zappi_powers = self.models.diverter.get_result('get_history_for_date', date, 'Z')
        eddi_timestamps, eddi_powers = self.models.diverter.get_result('get_history_for_date', date, 'E')
        battery_timestamps, battery_data = self.models.solar.get_result('get_battery_history_for_date', date)
        heat_pump_timestamps, heat_pump_data = self.models.heat_pump.get_result('get_history_for_date', date)

        self._plot_history_data(solar_timestamps, solar_data, zappi_timestamps, zappi_powers,
                                eddi_timestamps, eddi_powers, heat_pump_timestamps, heat_pump_data,
                                battery_timestamps, battery_data)

    @mainthread
    @popup_on_error('History plotting', _end_refreshing_history)
    def _plot_history_data(self, solar_timestamps, solar_data,
                           zappi_timestamps, zappi_powers,
                           eddi_timestamps, eddi_powers,
                           heat_pump_timestamps, heat_pump_data,
                           battery_timestamps, battery_data):
        production_power = solar_data['production']
        load_power = solar_data['consumption']
        export_power = solar_data['export']
        import_power = solar_data['purchased']

        ref_timestamps = solar_timestamps
        car_charge_power = normalise_to_timestamps(ref_timestamps, zappi_timestamps,
                                                   zappi_powers['total_power'])
        immersion_power = normalise_to_timestamps(ref_timestamps, eddi_timestamps,
                                                  eddi_powers['total_power'])
        dhw_power = normalise_to_timestamps(ref_timestamps, heat_pump_timestamps,
                                            heat_pump_data['DHW_power'])
        heating_power = normalise_to_timestamps(ref_timestamps, heat_pump_timestamps,
                                                heat_pump_data['heating_power'])
        legionnaires_power = normalise_to_timestamps(ref_timestamps, heat_pump_timestamps,
                                                     heat_pump_data['legionnaires_power'])
        combined_power = normalise_to_timestamps(ref_timestamps, heat_pump_timestamps,
                                                 heat_pump_data['combined_power'])
        unknown_heat_pump_power = normalise_to_timestamps(ref_timestamps, heat_pump_timestamps,
                                                          heat_pump_data['unknown_power'])
        battery_grid_charging = normalise_to_timestamps(ref_timestamps, battery_timestamps,
                                                        battery_data['charge_power_from_grid'])
        battery_solar_charging = normalise_to_timestamps(ref_timestamps, battery_timestamps,
                                                         battery_data['charge_power_from_solar'])
        battery_discharging = normalise_to_timestamps(ref_timestamps, battery_timestamps,
                                                      battery_data['discharge_power'])
        battery_state = normalise_to_timestamps(ref_timestamps, battery_timestamps,
                                                battery_data['charge_percentage'])

        remaining_load = load_power - (car_charge_power + immersion_power
                                       + dhw_power + heating_power
                                       + legionnaires_power + combined_power + unknown_heat_pump_power
                                       + battery_grid_charging)

        solar_production = production_power + battery_solar_charging - battery_discharging
        solar_consumption = solar_production - (export_power + battery_solar_charging)

        if battery_data['charge_from_grid_energy'] > 0:
            battery_energy_delta = battery_data['stored_energy'][-1] - battery_data['stored_energy'][0]
            total_consumption = solar_data['consumption_energy'] + battery_energy_delta
        else:
            total_consumption = solar_data['consumption_energy']
        battery_discharge_energy = battery_data['discharge_energy']
        solar_production_energy = solar_data['production_energy']
        export_energy = solar_data['export_energy']
        battery_solar_charging_energy = battery_data['charge_from_solar_energy']
        solar_consumption_energy = (solar_production_energy
                                    - (export_energy + battery_solar_charging_energy))

        remaining_energy = (solar_data['consumption_energy']
                            - (heat_pump_data['heating_energy']
                               + heat_pump_data['DHW_energy']
                               + heat_pump_data['legionnaires_energy']
                               + heat_pump_data['combined_energy']
                               + heat_pump_data['unknown_energy']
                               + zappi_powers['total_energy']
                               + eddi_powers['total_energy']
                               )
                            )
        consumption_color = (0.84, 0.00, 0.00)
        battery_color = (0.00, 0.75, 0.00)
        solar_color = (0.00, 0.9, 0.00)
        export_color = (0.58, 0.05, 0.31)
        import_color = (0.5, 0.5, 0.5)
        colors = ((0.26, 0.46, 0.91),  # car
                  (0.26, 0.84, 0.91),  # immersion
                  (1.00, 0.50, 0.00),  # DHW
                  (1.00, 0.75, 0.25),  # heating
                  (1.00, 0.50, 0.00),  # legionnaires
                  (1.00, 0.50, 0.00),  # combined
                  (1.00, 0.50, 0.00),  # unknown HP
                  battery_color,  # Battery
                  consumption_color,  # Other
                  )
        hatching = (None,  # car
                    None,  # immersion
                    None,  # DHW
                    None,  # heating
                    '||',  # legionnaires
                    '//',  # combined
                    '*',  # unknown HP
                    None,  # Battery
                    None,  # Other
                    )

        history_panel = self.root.ids.history.ids.graph_panel
        fig = plt.figure()
        destination_ax, production_ax, consumption_ax = fig.subplots(1, 3, sharey=True)
        self.labelled_stacked_bar(consumption_ax,
                                  (solar_consumption_energy,
                                   battery_solar_charging_energy,
                                   export_energy,
                                   ),
                                  total_value=solar_data['production_energy'],
                                  colors=(consumption_color, battery_color, export_color)
                                  )
        self.labelled_stacked_bar(production_ax,
                                  (solar_consumption_energy,
                                   battery_discharge_energy,
                                   solar_data['purchased_energy'],
                                   ),
                                  total_value=total_consumption,
                                  colors=(consumption_color, battery_color, import_color)
                                  )
        self.labelled_stacked_bar(destination_ax,
                                  (zappi_powers['total_energy'], eddi_powers['total_energy'],
                                   heat_pump_data['DHW_energy'], heat_pump_data['heating_energy'],
                                   heat_pump_data['legionnaires_energy'],
                                   heat_pump_data['combined_energy'], heat_pump_data['unknown_energy'],
                                   battery_data['charge_from_grid_energy'],
                                   remaining_energy,
                                   ),
                                  total_value=total_consumption,
                                  colors=colors, hatching=hatching)
        widget = FigureCanvasKivyAgg(fig)
        widget.size_hint_y = None
        widget.height = self.root.width * 0.5
        history_panel.add_widget(widget)

        ref_hours = ref_timestamps.total_hours()
        self._plot_to_history_panel(ref_hours, (car_charge_power,
                                                immersion_power,
                                                dhw_power,
                                                heating_power,
                                                legionnaires_power,
                                                combined_power,
                                                unknown_heat_pump_power,
                                                battery_grid_charging,
                                                remaining_load,
                                                ),
                                    labels=('Car charge', 'Immersion', 'DWH', 'Heating',
                                            'Legionnaires', 'Combined HP', 'Unknown HP',
                                            'Battery charging', 'Other'),
                                    colors=colors, hatch=hatching,
                                    )
        # plt.plot(ref_hours, load_power/1000, linestyle='--')

        self._plot_to_history_panel(ref_hours, (solar_consumption,
                                                battery_discharging,
                                                import_power,
                                                ),
                                    labels=('Solar consumption', 'Battery discharging', 'Import'),
                                    colors=(solar_color, battery_color, import_color)
                                    )
        # plt.plot(ref_hours, load_power/1000, linestyle='--')

        self._plot_to_history_panel(ref_hours, (solar_consumption,
                                                battery_solar_charging,
                                                export_power
                                                ),
                                    labels=('Consumption', 'Battery charging', 'Export'),
                                    colors=(consumption_color, battery_color, export_color)
                                    )

        ax = self._plot_to_history_panel(ref_hours, battery_state, convert_powers=False,
                                         # labels=('Battery state', ),
                                         plot_fun=plt.plot,
                                         )
        ax.set_ylim([0, 100])

    def labelled_stacked_bar(self, axes, values, total_value, colors=None, hatching=None):
        bars = stacked_bar([0], *[v/1000 for v in values],
                           ax=axes,
                           total_width=1,
                           colors=colors, hatch=hatching)
        labels = []
        for bar in bars:
            if bar.datavalues[0] > 0.1:
                val = bar.datavalues[0]
                bar_base = bar[0].xy[1]
                label_height = bar_base + 0.5 * val
                text = self._bar_label(val * 1000)  # convert val back to Wh
                labels.append(axes.text(0.6, label_height, text, horizontalalignment='left'))
        axes.set_ylim([0, (total_value / 1000) * 1.1])
        axes.set_xlim([-0.5, 1.5])
        # Label the total
        axes.text(0., (total_value / 1000) * 1.02,
                  self._bar_label(total_value),
                  horizontalalignment='center')
        plt.xticks([])
        plt.tight_layout()
        adjust_text(labels, only_move={'text': 'y'}, autoalign=False, text_from_points=False,
                    save_steps=False, ha='left', ax=axes)

    @staticmethod
    def _bar_label(val):
        # if val < 100:
        #     text = f'{val:.3g} Wh'
        # else:
        #     text = f'{val/1000:.3g} kWh'
        text = f'{val / 1000:.3g}'
        return text

    def _plot_to_history_panel(self, x, y, plot_fun=plt.stackplot, hatch=None,
                               convert_powers: bool = True, **kwargs):
        history_panel = self.root.ids.history.ids.graph_panel
        fig = plt.figure()
        if convert_powers:
            y = np.asarray(y) / 1000
        plots = plot_fun(x, y, **kwargs)
        if hatch is not None:
            for stack, hatch in zip(plots, hatch):
                if hatch is not None:
                    stack.set_hatch(hatch)
        if 'labels' in kwargs:
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
