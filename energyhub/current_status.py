from kivy.properties import ObjectProperty, AliasProperty
from kivy.clock import Clock
from kivy.uix.relativelayout import RelativeLayout
from kivy.utils import platform

from energyhub.models.model_set import ModelSet


class CurrentStatus(RelativeLayout):
    models: ModelSet = ObjectProperty()

    def __init__(self, **kw):
        super().__init__(**kw)
        Clock.schedule_interval(lambda x: self._check_refreshing(), 1)

    @staticmethod
    def calculate_arrow_size(power):
        if power == 0:
            return 0
        else:
            size = (15 + (30 * power / 5000))
            if platform == 'android':
                size = (25 + (70 * power / 5000))
            return size

    def refresh(self):
        for model in self.models:
            model.refresh()

    def check_pull_refresh(self, view):
        if view.scroll_y < 2 or self.refreshing:
            return
        self.refresh()

    def _get_refreshing(self):
        return any(model.refreshing for model in self.models)

    def _set_refreshing(self, value):
        self._refreshing = value
        return True

    def _check_refreshing(self):
        self.refreshing = self._get_refreshing()

    @staticmethod
    def small_size():
        return 25 if platform == 'android' else 15

    refreshing = AliasProperty(
        _get_refreshing,
        setter=_set_refreshing,
        cache=False,
    )

