import datetime
from abc import ABC, abstractmethod
from threading import Thread
from typing import Dict

import numpy as np
from kivy.clock import mainthread
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty


class BaseModel(EventDispatcher, ABC):
    stale = BooleanProperty(True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection = None
        self.thread = None

    def connect(self):
        self.thread = Thread(target=self._connect)
        self.thread.start()

    @abstractmethod
    def _connect(self):
        raise NotImplementedError

    def refresh(self):
        self.stale = True
        self.thread = Thread(target=self._refresh)
        self.thread.start()

    @abstractmethod
    def _refresh(self):
        raise NotImplementedError

    @abstractmethod
    @mainthread
    def _update_properties(self, data):
        raise NotImplementedError

    @mainthread
    def update_properties(self, data=None):
        self._update_properties(data)
        self.stale = False

    @abstractmethod
    def get_history_for_date(self, date: datetime.date) -> (np.ndarray, Dict[str, np.ndarray]):
        raise NotImplementedError
