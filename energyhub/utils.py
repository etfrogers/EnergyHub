import datetime
import functools
import ssl
import textwrap
from contextlib import AbstractContextManager
from typing import Sequence, Callable

import numpy as np
from kivy import platform
from kivy.clock import mainthread
from kivy.uix.label import Label
from kivy.uix.popup import Popup


def list_to_dict(list_of_kv_pairs):
    return {v['key']: v['value'] for v in list_of_kv_pairs}


def km_to_miles(km):
    return 0.621371 * km


def popup_on_error(label: str, cleanup_function: Callable = None):
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception as err:
                _warning(label + ' API Error', f'{err.__class__.__name__} : {err}')
                return None
            finally:
                if cleanup_function is not None:
                    self, *_ = args  # assume first arg is self
                    cleanup_function(self)
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


class TimestampArray(np.ndarray):
    def total_hours(self):
        return timestamps_to_hours(self)


def normalise_to_timestamps(ref_ts: TimestampArray, data_ts: TimestampArray, data: np.ndarray,
                            mode: str = 'preceding'):
    ref_hours = ref_ts.total_hours()
    data_hours = data_ts.total_hours()
    if mode == 'midpoint':
        bin_edges = np.mean(np.vstack((ref_hours[:-1], ref_hours[1:])), axis=0)
    elif mode == 'preceding':
        bin_edges = ref_hours[1:]
    elif mode == 'following':
        bin_edges = ref_hours[:-1]
    # 0 and max(data) are implicit bin_edges in np.digitize
    bin_indices = np.digitize(data_hours, bin_edges)
    counts_per_bin = np.bincount(bin_indices, minlength=ref_ts.size)
    total_data_in_bin = np.bincount(bin_indices, weights=data, minlength=ref_ts.size)
    mean_data_in_bin = total_data_in_bin / counts_per_bin
    return mean_data_in_bin
