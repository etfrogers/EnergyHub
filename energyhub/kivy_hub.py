
from kivy.app import App
from kivy.properties import BooleanProperty
from kivy.utils import platform

from matplotlib import pyplot as plt

from energyhub.models.car_models import JLRCarModel
from energyhub.models.diverter_models import MyEnergiModel
from energyhub.models.heat_pump_models import EcoforestModel
from energyhub.models.model_set import ModelSet
from energyhub.models.mvhr_models import ZehnderModel
from energyhub.models.solar_models import SolarEdgeModel
from energyhub.config import config

# kivy.require('1.0.7')

from kivy.core.window import Window
if platform != 'android':
    Window.size = (1440/4, 3216/4)
    plt.rcParams['font.size'] = 8
else:
    plt.rcParams['font.size'] = 24


# TODO House icon
# TODO Nest integration
# TODO Car status indication
# TODO
#   refresh on resume
#   more current status
# TODO save state?
# TODO caching of myenergi/solar_edge history
# TODO fix history bugs on 29/12, 26/12
# TODO settings
# TODO Fix tab strip width
# TODO planning tab
#   weather icons
#   boost by time, kWh, miles
#   Days car will be out, and distance
#   Notification of low prices
#   Plotting of prices
# TODO Heat pump COP - inst ++
# TODO kivy logging


class EnergyHubApp(App):
    connected = BooleanProperty(True)

    def __init__(self, **kwargs):
        super(EnergyHubApp, self).__init__(**kwargs)
        solar_model = SolarEdgeModel(config.data['solar-edge']['api-key'],
                                     config.data['solar-edge']['site-id'],
                                     config.timezone,
                                     timeout=10,
                                     should_connect=self.connected)
        car_model = JLRCarModel(config.data['jlr']['username'],
                                config.data['jlr']['password'],
                                config.data['jlr'].get('vin', None),
                                timeout=60,
                                should_connect=self.connected)
        heat_pump_model = EcoforestModel(config.data['ecoforest']['server'],
                                         config.data['ecoforest']['port'],
                                         config.data['ecoforest']['serial-number'],
                                         config.data['ecoforest']['auth-key'],
                                         timezone=config.timezone,
                                         timeout=60,
                                         should_connect=self.connected)
        diverter_model = MyEnergiModel(config.data['myenergi']['username'],
                                       config.data['myenergi']['api-key'],
                                       config.timezone,
                                       timeout=10,
                                       should_connect=self.connected)
        mvhr_model = ZehnderModel('',
                                  config.data['zehnder']['api-key'],
                                  timeout=10,
                                  should_connect=self.connected)

        self.models = ModelSet(solar=solar_model,
                               car=car_model,
                               heat_pump=heat_pump_model,
                               diverter=diverter_model,
                               mvhr=mvhr_model)

    def build(self):
        super(EnergyHubApp, self).build()
        if self.connected:
            for model in self.models:
                model.connect()
            for model in self.models:
                model.get_result('connect')
            self.status_panel.refresh()

    @property
    def status_panel(self):
        return self.root.ids.cs_container.ids.status_panel

    @property
    def history_panel(self):
        return self.root.ids.history_container.ids.history_panel

    def on_pause(self):
        return True
