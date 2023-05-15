import datetime
from typing import Dict

import numpy as np
from kivy.properties import NumericProperty

# import pyzehndercloud
from energyhub.models.model import BaseModel
# from example import InteractiveAuth


class ZehnderModel(BaseModel):

    supply_temperature = NumericProperty(18)
    exhaust_temperature = NumericProperty(18)
    outdoor_temperature = NumericProperty(18)
    extract_temperature = NumericProperty(18)
    supply_humidity = NumericProperty(65)
    exhaust_humidity = NumericProperty(65)
    outdoor_humidity = NumericProperty(65)
    extract_humidity = NumericProperty(65)

    def __init__(self, username: str, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.api_key = api_key
        self._session = None
        self._device = None

    async def _connect(self):
        # self._session = aiohttp.ClientSession()
        # auth = InteractiveAuth(self._session, username=self.username, api_key=self.api_key)
        self.connection = None #pyzehndercloud.ZehnderCloud(self._session, auth)
        devices = await self.connection.get_devices()
        self._device = devices[0]

    async def _refresh(self):
        # Get device details
        status = await self.connection.get_device_details(self._device)
        self.update_properties(status)

    def _update_properties(self, data):
        self.supply_temperature = data['supplyTemperature']
        self.exhaust_temperature = data['exhaustTemperature']
        self.outdoor_temperature = data['outdoorTemperature']
        self.extract_temperature = data['extractTemperature']
        self.supply_humidity = data['supplyHumidity']
        self.exhaust_humidity = data['exhaustHumidity']
        self.outdoor_humidity = data['outdoorHumidity']
        self.extract_humidity = data['extractHumidity']

    def _get_history_for_date(self, date: datetime.date) -> (np.ndarray, Dict[str, np.ndarray]):
        pass
