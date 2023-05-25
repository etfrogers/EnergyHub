from threading import Thread

import numpy as np
from kivy.app import App
from kivy.properties import ObjectProperty, AliasProperty, NumericProperty
from matplotlib import pyplot as plt


from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock, mainthread
from adjustText import adjust_text
# noinspection PyUnresolvedReferences
from kivy.garden.matplotlib import FigureCanvasKivyAgg

from ecoforest.plotting import stacked_bar
from energyhub.models.model_set import ModelSet
from energyhub.utils import popup_on_error, normalise_to_timestamps
from energyhub.config import logger


class HistoryPanel(BoxLayout):
    models: ModelSet = ObjectProperty()
    number_of_graphs = NumericProperty(0)

    def __init__(self, **kwargs):
        # build graphs needs to be called after initialisation to get sizes correct
        super().__init__(**kwargs)
        self._refreshing = False
        Clock.schedule_once(lambda x: Thread(self.build_graphs()).start(), 0.1)

    def check_pull_refresh(self, view):
        logger.debug(view.scroll_y)
        logger.debug(self._refreshing)
        if view.scroll_y <= 2 or self._refreshing:
            return
        self.build_graphs()

    def _end_refreshing(self):
        self._refreshing = False

    @popup_on_error('History fetching', _end_refreshing)
    def build_graphs(self, date=None):
        self._refreshing = True
        date_picker = self.ids.history_date
        self.clear_graphs()
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

        self._plot_data(solar_timestamps, solar_data, zappi_timestamps, zappi_powers,
                        eddi_timestamps, eddi_powers, heat_pump_timestamps, heat_pump_data,
                        battery_timestamps, battery_data)

    def clear_graphs(self):
        graph_panel = self.ids.graph_panel
        for graph_widget in graph_panel.children:
            plt.close(graph_widget.figure)
        graph_panel.clear_widgets()
        self.number_of_graphs = 0
        self.ids.scroll_panel.scroll_y = 0

    @mainthread
    @popup_on_error('History plotting', _end_refreshing)
    def _plot_data(self, solar_timestamps, solar_data,
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

        # plt.plot(solar_timestamps.total_hours(), load_power,
        #          # heat_pump_timestamps.total_hours(), heat_pump_data['heating_power'],
        #          heat_pump_timestamps.total_hours(), (heat_pump_data['DHW_power'] + heat_pump_data['heating_power']
        #                                               + heat_pump_data['legionnaires_power']
        #                                               + heat_pump_data['combined_power']
        #                                               + heat_pump_data['unknown_power']),
        #          # ref_timestamps.total_hours(), heating_power,
        #          # ref_timestamps.total_hours(), remaining_load,
        #          eddi_timestamps.total_hours(), eddi_powers['total_power'],
        #          zappi_timestamps.total_hours(), zappi_powers['total_power'],
        #          battery_timestamps.total_hours(), battery_data['charge_power_from_grid'],
        #          )
        # plt.show()

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

        history_panel = self.ids.graph_panel
        fig = plt.figure()
        self.number_of_graphs += 1
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
        widget.height = self.graph_height
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

    @staticmethod
    def labelled_stacked_bar(axes, values, total_value, colors=None, hatching=None):
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
                text = HistoryPanel._bar_label(val * 1000)  # convert val back to Wh
                labels.append(axes.text(0.6, label_height, text, horizontalalignment='left'))
        axes.set_ylim([0, (total_value / 1000) * 1.1])
        axes.set_xlim([-0.5, 1.5])
        # Label the total
        axes.text(0., (total_value / 1000) * 1.02,
                  HistoryPanel._bar_label(total_value),
                  horizontalalignment='center')
        plt.xticks([])
        plt.tight_layout()
        adjust_text(labels, only_move={'text': 'y'}, autoalign=False, text_from_points=False,
                    save_steps=False, ha='left', ax=axes)

    @staticmethod
    def _bar_label(val):
        text = f'{val / 1000:.3g}'
        return text

    def _plot_to_history_panel(self, x, y, plot_fun=plt.stackplot, hatch=None,
                               convert_powers: bool = True, **kwargs):
        history_panel = self.ids.graph_panel
        fig = plt.figure()
        self.number_of_graphs += 1
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
        widget.height = self.graph_height
        history_panel.add_widget(widget)
        return plt.gca()

    # noinspection PyMethodMayBeStatic
    def _graph_height(self):
        # as this is a getter method for an alias property, it cannot be static
        if root_widget := App.get_running_app().root:
            return root_widget.width * 0.5
        else:
            return 1

    def _get_height(self):
        return self.graph_height * self.number_of_graphs

    graph_height = AliasProperty(
        _graph_height,
    )

    total_graph_height = AliasProperty(
        _get_height,
        cache=False,
        bind=['number_of_graphs']
    )