import datetime
import ssl
import textwrap
from contextlib import AbstractContextManager
from typing import Sequence

import numpy as np
from kivy import platform
from kivy.clock import mainthread
from kivy.uix.label import Label
from kivy.uix.popup import Popup


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


def timestamps_to_hours(times: Sequence[datetime.datetime]):
    date = times[0].date()
    midnight = datetime.datetime.combine(date, datetime.time(0))
    return np.array([(t - midnight).total_seconds() / (60 * 60) for t in times])


# noinspection PyUnresolvedReferences,PyProtectedMember
class NoSSLVerification(AbstractContextManager):
    def __enter__(self):
        self._original_context = ssl._create_default_https_context
        if platform == 'android':
            ssl._create_default_https_context = ssl._create_unverified_context

    def __exit__(self, exc_type, exc_val, exc_tb):
        ssl._create_default_https_context = self._original_context
