from kivy.event import EventDispatcher
from kivy.properties import ObjectProperty, NumericProperty, AliasProperty

from energyhub.models.car_models import JLRCarModel
from energyhub.models.diverter_models import MyEnergiModel
from energyhub.models.heat_pump_models import EcoforestModel
from energyhub.models.mvhr_models import ZehnderModel
from energyhub.models.solar_models import SolarEdgeModel


class ModelSet(EventDispatcher):
    solar = ObjectProperty()
    car = ObjectProperty()
    heat_pump = ObjectProperty()
    diverter = ObjectProperty()
    mvhr = ObjectProperty()
    _solar_edge_load = NumericProperty(0)
    _heating_power = NumericProperty(0)
    _dhw_power = NumericProperty(0)
    _car_charger_power = NumericProperty(0)
    _immersion_power = NumericProperty(0)

    def __init__(self, /, solar: SolarEdgeModel, car: JLRCarModel, heat_pump: EcoforestModel, diverter: MyEnergiModel,
                 mvhr: ZehnderModel,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.solar = solar
        self.car = car
        self.heat_pump = heat_pump
        self.diverter = diverter
        self.mvhr = mvhr
        self.solar.bind(load=self.setter('_solar_edge_load'))
        self.heat_pump.bind(heating_power=self.setter('_heating_power'),
                            dhw_power=self.setter('_dhw_power'),
                            )
        self.diverter.bind(immersion_power=self.setter('_immersion_power'),
                           car_charger_power=self.setter('_car_charger_power'),
                           )

    def __iter__(self):
        return iter((self.solar, self.car, self.heat_pump, self.diverter, self.mvhr))

    def _get_remaining_load(self):
        return self.solar.load - (self.diverter.immersion_power
                                  + self.diverter.car_charger_power
                                  + self.heat_pump.heating_power
                                  + self.heat_pump.dhw_power)

    def _get_bottom_arms_power(self):
        return (self.diverter.car_charger_power
                + self.diverter.immersion_power
                + self.heat_pump.dhw_power)

    remaining_load = AliasProperty(
        _get_remaining_load,
        bind=['_solar_edge_load', '_car_charger_power', '_immersion_power', '_heating_power', '_dhw_power']
    )
    _bottom_arms_power = AliasProperty(
        _get_bottom_arms_power,
        bind=['_car_charger_power', '_immersion_power', '_dhw_power']
    )
