
from kivy.app import App
from kivy.utils import platform

from matplotlib import pyplot as plt

from energyhub.models.car_models import JLRCarModel
from energyhub.models.diverter_models import MyEnergiModel
from energyhub.models.heat_pump_models import EcoforestModel
from energyhub.models.model_set import ModelSet
from energyhub.models.mvhr_models import ZehnderModel
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
        solar_model = SolarEdgeModel(config.data['solar-edge']['api-key'],
                                     config.data['solar-edge']['site-id'],
                                     config.timezone,
                                     timeout=10)
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
        mvhr_model = ZehnderModel(config.data['zehnder']['username'], config.data['zehnder']['api-key'])

        self.models = ModelSet(solar=solar_model,
                               car=car_model,
                               heat_pump=heat_pump_model,
                               diverter=diverter_model,
                               mvhr=mvhr_model)

    def build(self):
        super(EnergyHubApp, self).build()
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


if __name__ == '__main__':
    app = EnergyHubApp()
    app.run()
