import datetime
from datetime import date, timedelta
from functools import partial
import kivy
from kivy.properties import ObjectProperty, BooleanProperty

kivy.require('1.4.0')

from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button


class DatePicker(BoxLayout):
    date = ObjectProperty()

    def __init__(self, *args, **kwargs):
        super(DatePicker, self).__init__(**kwargs)
        self.date = date.today()
        self.orientation = "vertical"
        self.month_names = ('January',
                            'February',
                            'March',
                            'April',
                            'May',
                            'June',
                            'July',
                            'August',
                            'September',
                            'October',
                            'November',
                            'December')
        if "month_names" in kwargs:
            self.month_names = kwargs['month_names']
        self.header = BoxLayout(orientation='horizontal',
                                size_hint=(1, 0.2))
        self.body = GridLayout(cols=7)
        self.add_widget(self.header)
        self.add_widget(self.body)

        self.populate_body()
        self.populate_header()

    @property
    def month_year_text(self):
        return self.month_names[self.date.month - 1] + ' ' + str(self.date.year)

    def populate_header(self, *args, **kwargs):
        self.header.clear_widgets()
        previous_month = Button(text="<", on_press=self.move_previous_month)
        next_month = Button(text=">", on_press=self.move_next_month)
        current_month = Label(text=self.month_year_text, size_hint=(2, 1))

        self.header.add_widget(previous_month)
        self.header.add_widget(current_month)
        self.header.add_widget(next_month)

    def populate_body(self, *args, **kwargs):
        self.body.clear_widgets()
        date_cursor = date(self.date.year, self.date.month, 1)
        for filler in range(date_cursor.isoweekday() - 1):
            self.body.add_widget(Label(text=""))
        while date_cursor.month == self.date.month:
            date_label = Button(text=str(date_cursor.day))
            date_label.bind(on_press=partial(self.set_date,
                                             day=date_cursor.day))
            if self.date.day == date_cursor.day:
                date_label.background_normal, date_label.background_down = date_label.background_down, date_label.background_normal
            self.body.add_widget(date_label)
            date_cursor += timedelta(days=1)

    def set_date(self, *args, **kwargs):
        self.date = date(self.date.year, self.date.month, kwargs['day'])
        self.populate_body()
        self.populate_header()

    def move_next_month(self, *args, **kwargs):
        if self.date.month == 12:
            self.date = date(self.date.year + 1, 1, self.date.day)
        else:
            self.date = date(self.date.year, self.date.month + 1, self.date.day)
        self.populate_header()
        self.populate_body()

    def move_previous_month(self, *args, **kwargs):
        if self.date.month == 1:
            self.date = date(self.date.year - 1, 12, self.date.day)
        else:
            self.date = date(self.date.year, self.date.month - 1, self.date.day)
        self.populate_header()
        self.populate_body()


class CollapsibleDatePicker(DatePicker):
    collapsed = BooleanProperty(True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_collapsed()
        self.header.height = '36sp'
        self.header.size_hint_y = None
        self.height = self.header.height

    def populate_header(self, *args, **kwargs):
        if self.collapsed:
            self._populate_collapsed_header()
        else:
            super().populate_header(*args, **kwargs)
            label = self.header.children[1]
            self.header.remove_widget(label)
            current_month = Button(text=self.month_year_text, size_hint=(2, 1),
                                   on_press=self.collapse)
            self.header.add_widget(current_month, index=1)

    def populate_body(self, *args, **kwargs):
        if self.collapsed:
            self.body.clear_widgets()
        else:
            super().populate_body(*args, **kwargs)

    def _populate_collapsed_header(self):
        self.header.clear_widgets()
        blank_button = Button(text='')
        previous_day = Button(text="<", on_press=self.move_previous_day)
        next_day = Button(text=">", on_press=self.move_next_day)
        go_to_today = Button(text=">|", on_press=self.go_to_today)
        current_date = Button(text=self.date.strftime('%d/%m/%y'), size_hint=(2, 1),
                              on_press=self.uncollapse)

        self.ids['date_label'] = current_date
        self.header.add_widget(blank_button)
        self.header.add_widget(previous_day)
        self.header.add_widget(current_date)
        self.header.add_widget(next_day)
        self.header.add_widget(go_to_today)

    def collapse(self, _=None):
        self.collapsed = True

    def uncollapse(self, _=None):
        self.collapsed = False

    def go_to_today(self, _):
        self.date = datetime.date.today()

    def move_next_day(self, _):
        if self.date < datetime.date.today():
            self.date = self.date + datetime.timedelta(days=1)

    def move_previous_day(self, _):
        self.date = self.date - datetime.timedelta(days=1)

    def on_collapsed(self, *args):
        if self.collapsed:
            self.body.height = '0dp'
            self.height = self.header.height
        else:
            self.body.height = self.body.width * 0.5
            self.height = self.header.height + self.body.height
        self.populate_header()
        self.populate_body()

    def on_date(self, *args):
        if self.collapsed:
            try:
                self.ids.date_label.text = self.date.strftime('%d/%m/%y')
            except AttributeError:
                pass

    def set_date(self, *args, **kwargs):
        super(CollapsibleDatePicker, self).set_date(*args, **kwargs)
        self.collapse()
