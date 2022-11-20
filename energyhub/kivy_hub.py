import datetime
import textwrap
import time
from threading import Thread
from typing import Optional, List, Dict, Sequence

import jlrpy
from kivy.app import App
from kivy.properties import NumericProperty, AliasProperty, StringProperty, BooleanProperty, DictProperty
from kivy.utils import platform
from kivy.clock import mainthread
import ssl
from contextlib import AbstractContextManager

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from matplotlib import pyplot as plt

# importing numpy
import numpy as np
from kivy.garden.matplotlib import FigureCanvasKivyAgg
from urllib3.exceptions import NewConnectionError

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
                _warning(label + ' API Error', str(err))
                return None
        return wrapper
    return decorator


@mainthread
def _warning(title: str, msg: str):
    Popup(title=title,
          content=Label(text=textwrap.fill(msg, 37)),
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
    stale_sources = DictProperty({'car': True, 'myenergi': True, 'heatpump': True, 'solaredge': True})

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

    def __init__(self, *args, **kwargs):
        super(EnergyHubApp, self).__init__(*args, **kwargs)
        self.car_connection: Optional[jlrpy.Connection] = None
        self.my_energi_connection: Optional[MyEnergiHost] = None
        self.solar_edge_connection: Optional[SolarEdgeClient] = None
        self.ecoforest_connection: Optional[EcoforestClient] = None

    def build(self):
        super(EnergyHubApp, self).build()
        self.car_connection = self._connect_car()
        self.my_energi_connection = self._connect_my_energi()
        self.solar_edge_connection = self._connect_solar_edge()
        self.ecoforest_connection = self._connect_ecoforest()
        self.refresh()

    @staticmethod
    @popup_on_error('Error initialising JLR')
    def _connect_car() -> jlrpy.Connection:
        with NoSSLVerification():
            conn = jlrpy.Connection(config.data['jlr']['username'],
                                    config.data['jlr']['password'])
            conn.refresh_tokens()
        return conn

    @staticmethod
    @popup_on_error('Error initialising MyEnergi')
    def _connect_my_energi() -> MyEnergiHost:
        return MyEnergiHost(config.data['myenergi']['username'],
                            config.data['myenergi']['api-key'])

    @staticmethod
    @popup_on_error('Error initialising SolarEdge')
    def _connect_solar_edge() -> SolarEdgeClient:
        return SolarEdgeClient(config.data['solar-edge']['api-key'],
                               config.data['solar-edge']['site-id'])

    @staticmethod
    @popup_on_error('Error initialising Ecoforest')
    def _connect_ecoforest() -> EcoforestClient:
        return EcoforestClient(config.data['ecoforest']['server'],
                               config.data['ecoforest']['port'],
                               config.data['ecoforest']['serial-number'],
                               config.data['ecoforest']['auth-key'])

    def on_pause(self):
        return True

    def refresh(self):
        self.stale_sources = {key: True for key in self.stale_sources}
        Thread(target=self._refresh_solar_edge).start()
        Thread(target=self._refresh_car).start()
        Thread(target=self._refresh_my_energi).start()
        Thread(target=self._refresh_heat_pump).start()
        self.build_history_graphs()

    @popup_on_error('MyEnergi')
    def _refresh_my_energi(self):
        if not self.my_energi_connection:
            self.my_energi_connection = self._connect_my_energi()
        with NoSSLVerification():
            self.my_energi_connection.refresh()
        self._update_my_energi_data()

    @mainthread
    def _update_my_energi_data(self):
        self.zappi_power = self.zappi.charge_rate
        self.eddi_power = self.eddi.charge_rate
        self.stale_sources['myenergi'] = False
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
        if not self.car_connection:
            self.car_connection = self._connect_car()
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
        self.stale_sources['car'] = False

    @popup_on_error('SolarEdge')
    def _refresh_solar_edge(self):
        if not self.solar_edge_connection:
            self.solar_edge_connection = self._connect_solar_edge()
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
        self.stale_sources['solaredge'] = False

    @popup_on_error('Ecoforest')
    def _refresh_heat_pump(self):
        if not self.ecoforest_connection:
            self.ecoforest_connection = self._connect_ecoforest()
        status = self.ecoforest_connection.get_current_status()
        self._update_heat_pump_data(status)

    @mainthread
    def _update_heat_pump_data(self, status):
        self.heat_pump_power = status['ElectricalPower']['value']
        self.outside_temperature = status['OutsideTemp']['value']
        if status['DHWDemand']['value']:
            self.dhw_power = self.heat_pump_power
            self.heating_power = 0
        elif status['HeatingDemand']['value']:
            self.heating_power = self.heat_pump_power
            self.dhw_power = 0
        else:
            print(status)
            # assert self.heat_pump_power == 0
            self.heating_power = 0
            self.dhw_power = 0
        self.stale_sources['heatpump'] = False

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

    @popup_on_error('History')
    def build_history_graphs(self, date=None):
        history_panel = self.root.ids.history
        date_picker = history_panel.ids.history_date
        history_panel.clear_widgets()
        history_panel.add_widget(date_picker)
        if date is None:
            date = date_picker.date
        data = self.solar_edge_connection.get_power_history_for_day(date)
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
        plt.plot(timestamps_to_hours(zappi_timestamps), np.array([p/1000 for p in zappi_powers.values()]).T)
        plt.xticks([0, 6, 12, 18, 24])
        history_panel.add_widget(FigureCanvasKivyAgg(fig))

        fig = plt.figure()
        plt.plot(timestamps_to_hours(eddi_timestamps), np.array([p/1000 for p in eddi_powers.values()]).T)
        plt.xticks([0, 6, 12, 18, 24])
        history_panel.add_widget(FigureCanvasKivyAgg(fig))

    @property
    def zappi(self):
        return self.my_energi_connection.state.zappi_list()[0]

    @property
    def eddi(self):
        return self.my_energi_connection.state.eddi_list()[0]


def timestamps_to_hours(times: Sequence[datetime.datetime]):
    date = times[0].date()
    midnight = datetime.datetime.combine(date, datetime.time(0))
    return np.array([(t - midnight).total_seconds() / (60 * 60) for t in times])


def zappi_dict_to_arrays(zappi_data: List[Dict]):
    timestamps = []
    import_power = []
    export_power = []
    charge_diverted = []
    charge_imported = []
    volts = []
    for datapoint in zappi_data:
        # entries with zero value are omitted from data
        timestamp = datetime.datetime(year=datapoint['yr'],
                                      month=datapoint['mon'],
                                      day=datapoint['dom'],
                                      hour=datapoint.get('hr', 0),  # hr may not be present
                                      minute=datapoint.get('min', 0),  # min may not be present
                                      )
        timestamps.append(timestamp)
        import_power.append(datapoint.get('imp', 0))
        export_power.append(datapoint.get('exp', 0))
        charge_diverted.append(datapoint.get('h1d', 0))
        charge_imported.append(datapoint.get('h1b', 0))
        volts.append(datapoint['v1'])
    timestamps = np.array(timestamps)
    import_power = np.array(import_power, dtype=float)
    export_power = np.array(export_power, dtype=float)
    charge_imported = np.array(charge_imported, dtype=float)
    charge_diverted = np.array(charge_diverted, dtype=float)
    volts = np.array(volts)/10
    to_watts = 4/volts
    import_power *= to_watts
    export_power *= to_watts
    charge_imported *= to_watts
    charge_diverted *= to_watts
    charging_power = charge_imported + charge_diverted
    powers = {'import': import_power,
              'export': export_power,
              'charge_diverted': charge_diverted,
              'charge_imported': charge_imported,
              'charging_power': charging_power,
              }
    return timestamps, powers


if __name__ == '__main__':
    app = EnergyHubApp()
    app.run()
