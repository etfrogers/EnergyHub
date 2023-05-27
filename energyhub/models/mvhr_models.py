import asyncio
import datetime
from typing import Dict

import aiohttp as aiohttp
import numpy as np
from kivy.properties import NumericProperty

import pyzehndercloud
from energyhub.config import logger
from energyhub.models.model import BaseModel
from energyhub.utils import popup_on_error
from pyzehndercloud.auth import InteractiveAuth


pyzehndercloud.zehndercloud._LOGGER = logger


class ZehnderModel(BaseModel):

    @popup_on_error('Zehnder Initialisation')
    def connect(self):
        self._event_loop.run_until_complete(self._connect())

    def refresh(self):
        self._event_loop.run_until_complete(self._refresh())

    def get_result(self, func_name, *args):
        pass

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
        self._event_loop = asyncio.new_event_loop()

    async def _connect(self):
        self._session = aiohttp.ClientSession()
        auth = InteractiveAuth(self._session, username=self.username, api_key=self.api_key)
        self.connection = pyzehndercloud.ZehnderCloud(self._session, auth, verify_ssl=False)
        devices = await self.connection.get_devices()
        if devices:
            self._device = devices[0]

    @popup_on_error('Zehnder Refresh', cleanup_function=BaseModel._finish_refresh)
    async def _refresh(self):
        if self._device:
            status = await self.connection.get_device_state(self._device)
            self.update_properties(status)

    @popup_on_error('Zehnder Refresh', cleanup_function=BaseModel._finish_refresh)
    def _update_properties(self, data):
        logger.debug('Zehnder status data: ', data.data)
        self.supply_temperature = data['systemSupplyTemp']
        self.exhaust_temperature = data['exhaustAirTemp']
        self.outdoor_temperature = data['systemOutdoorTemp']
        self.extract_temperature = data['extractAirTemp']
        self.supply_humidity = data['systemSupplyHumidity']
        self.exhaust_humidity = data['exhaustAirHumidity']
        self.outdoor_humidity = data['systemOutdoorHumidity']
        self.extract_humidity = data['extractAirHumidity']

    def _get_history_for_date(self, date: datetime.date) -> (np.ndarray, Dict[str, np.ndarray]):
        pass
