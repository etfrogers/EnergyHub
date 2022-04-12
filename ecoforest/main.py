import datetime

import requests
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

CSV_DATE_FORMAT = '%Y/%m/%d %H:%M:%S'
EXPLORE_UNUSED_DATA = False


class Dataset:
    def __init__(self, date: datetime.date):
        self.date = date
        use_cache = True
        if use_cache:
            try:
                with open(self._cache_file) as file:
                    contents = file.read()
            except FileNotFoundError:
                contents = self.get_data_from_server()
                if self.date != datetime.datetime.today().date():
                    # do not cache today's data as it will change
                    with open(self._cache_file, 'w') as file:
                        file.write(contents)
        else:
            contents = self.get_data_from_server()
        self.timestamps, self._full_data = self.process_file_data(contents)

        self.heating = self.consumption = self.cooling = None
        self.dhw_temp = self.heating_buffer_temp = self.cooling_buffer_temp = None
        self.production_supply = self.production_return = self.brine_supply = self.brine_return = None
        self.outdoor_temp = None

        # indices taken from Javascript plotting code
        # (need to subtract 2 from the indices used there to allow for serial and timestamp)
        mapping = {24: 'consumption',
                   25: 'heating',
                   26: 'cooling',
                   10: 'dhw_temp',
                   # no index for 'pool'
                   13: 'heating_buffer_temp',
                   14: 'cooling_buffer_temp',
                   15: 'production_supply',
                   16: 'production_return',
                   17: 'brine_supply',
                   18: 'brine_return',
                   11: 'outdoor_temp',
                   19: 'zone_1',
                   20: 'zone_2',
                   21: 'zone_3',
                   22: 'zone_4',
                   }
        for index, name in mapping.items():
            setattr(self, name, self._full_data[:, index] / 10)
        if EXPLORE_UNUSED_DATA:
            speeds = [7, 8]
            plt.figure()
            for i in speeds:
                plt.plot(self.timestamps, self._full_data[:, i] / 10, label=str(i))
            plt.gca().xaxis.set_major_formatter(self._time_format())
            plt.legend()
            plt.title('Speeds')
            unused_indices = np.array([i for i in range(self._full_data.shape[1])
                                       if not (i in mapping.keys() or i in speeds)])

            plt.figure()
            for i in unused_indices:
                data = self._full_data[:, i] / 10
                if np.all(np.isclose(data, 0)):
                    continue
                plt.plot(self.timestamps, data, label=str(i))
            plt.gca().xaxis.set_major_formatter(self._time_format())
            plt.legend()

    @staticmethod
    def total_power(series: np.ndarray):
        # 5 minute intervals, means 12 to an hour, so one 1kW at one point is 1/12 kWh
        return np.sum(series) / 12

    @property
    def total_consumption(self):
        return self.total_power(self.consumption)

    @property
    def total_heating(self):
        return self.total_power(self.heating)

    @property
    def cop(self):
        return self.heating / self.consumption

    @property
    def daily_cop(self):
        return np.nanmean(self.cop)

    def chunks(self):
        is_on = (self.consumption != 0).astype(int)
        switches = np.diff(is_on)
        starts = np.nonzero(switches == 1)[0]
        ends = np.nonzero(switches == -1)[0]
        # line below will fail if on over midnight.
        # If this occurs a special case will be needed
        assert starts.size == ends.size
        # returns inclusive inds (first non element and last nonzero element)
        return zip(starts+1, ends)

    def plot(self, axes=None):
        if axes is None:
            plt.figure()
            ax1 = plt.subplot(1, 1, 1)
            ax2 = ax1.twinx()
        else:
            ax1, ax2 = axes
        ax1.plot(self.timestamps, self.consumption, label=f'Electrical power: {self.total_consumption:.2f} kWh', color='red')
        ax1.plot(self.timestamps, self.heating, label=f'Heating power: {self.total_heating:.2f} kWh', color='lightgreen')
        ax1.set_ylabel('kW')
        ax2.plot(self.timestamps, self.cop, label=f'Mean COP: {self.daily_cop:.2f}')
        ax1.legend(loc='upper right')
        ax2.legend(loc='upper left')
        plt.suptitle(f'{self.date_str}')
        ax1.xaxis.set_major_formatter(self._time_format())

        x_data = []
        y_data = []
        labels = []
        for chunk in self.chunks():
            chunk_inds = range(chunk[0], chunk[1]+1)
            chunk_heating = self.heating[chunk_inds]
            chunk_consumption = self.consumption[chunk_inds]
            chunk_cop = self.cop[chunk_inds]
            assert not np.any(np.isnan(chunk_cop))
            x_data.append(self.timestamps[chunk[0]])
            y_data.append(np.max(chunk_heating)+0.1)
            label = (f'{self.total_power(chunk_consumption):.1f} kWh\n'
                     + f'PF: {np.mean(chunk_cop):.2f}')
            labels.append(label)
            # ax1.text(chunk[0], np.max(chunk_heating)+0.1,
            #          f'{self.total_power(chunk_consumption):.1f} kWh\n'
            #          f'PF: {np.mean(chunk_cop):.2f}')
        txt_height = 0.07 * (ax1.get_ylim()[1] - ax1.get_ylim()[0])
        txt_width = 0.12 * (ax1.get_xlim()[1] - ax1.get_xlim()[0])
        txt_width = datetime.timedelta(hours=1)
        # Get the corrected text positions, then write the text.
        text_positions = get_text_positions(x_data, y_data, txt_width, txt_height)
        text_plotter(x_data, y_data, labels, text_positions, ax1, txt_width, txt_height)

        plt.figure()
        plt.plot(self.timestamps, self.dhw_temp, label='DHW')
        plt.plot(self.timestamps, self.heating_buffer_temp, label='Heating Buffer')
        plt.plot(self.timestamps, self.production_supply, label='Production Flow')
        plt.plot(self.timestamps, self.production_return, label='Production Return')
        plt.plot(self.timestamps, self.brine_supply, label='Brine Return')
        plt.plot(self.timestamps, self.brine_return, label='Brine Return')
        plt.gca().xaxis.set_major_formatter(self._time_format())
        plt.legend()

        plt.figure()
        plt.plot(self.timestamps, self.outdoor_temp, label='Outdoor')
        plt.gca().xaxis.set_major_formatter(self._time_format())
        plt.legend()

        plt.show()
        return [ax1, ax2]

    @staticmethod
    def _time_format():
        return DateFormatter("%H:%M")

    @property
    def date_str(self):
        return self.date.strftime('%Y-%m-%d')

    @property
    def _cache_file(self):
        return f'data/{self.date_str}.csv'

    def get_data_from_server(self):
        server = '192.168.1.147'
        port = '8000'
        data_dir = 'historic'
        serial = '**REMOVED**'
        filename = f'{self.date_str}_{serial}_1_historico.csv'
        url = f'https://{server}:{port}/{data_dir}/{filename}'
        key = '**REMOVED**'
        response = requests.get(url,
                                verify=False,
                                headers={'Authorization': f'Basic {key}'})
        return response.text

    @staticmethod
    def process_file_data(contents):
        headers, *lines = contents.split('\n')
        timestamps = []
        data = []
        for line in lines:
            if line:
                _, timestamp, *entry = line.split(';')[:-1]
                timestamps.append(datetime.datetime.strptime(timestamp, CSV_DATE_FORMAT))
                data.append([float(val) for val in entry])
        data = np.array(data)
        return timestamps, data


def get_text_positions(x_data, y_data, txt_width, txt_height):
    """https://stackoverflow.com/questions/8850142/matplotlib-overlapping-annotations"""
    a = list(zip(y_data, x_data))
    text_positions = y_data.copy()
    for index, (y, x) in enumerate(a):
        local_text_positions = [i for i in a if i[0] > (y - txt_height)
                                and (abs(i[1] - x) < txt_width * 2) and i != (y, x)]
        if local_text_positions:
            sorted_ltp = sorted(local_text_positions)
            if abs(sorted_ltp[0][0] - y) < txt_height:  # True == collision
                differ = np.diff(sorted_ltp, axis=0)
                a[index] = (sorted_ltp[-1][0] + txt_height, a[index][1])
                text_positions[index] = sorted_ltp[-1][0] + txt_height
                for k, (j, m) in enumerate(differ):
                    # j is the vertical distance between words
                    if j > txt_height * 2:  # if True then room to fit a word in
                        a[index] = (sorted_ltp[k][0] + txt_height, a[index][1])
                        text_positions[index] = sorted_ltp[k][0] + txt_height
                        break
    return text_positions


def text_plotter(x_data, y_data, labels, text_positions, axis, txt_width, txt_height):
    """https://stackoverflow.com/questions/8850142/matplotlib-overlapping-annotations"""
    for x, y, l, t in zip(x_data, y_data, labels, text_positions):
        axis.text(x - txt_width, 1.01*t, l, rotation=0, color='k')
        if y != t:
            axis.arrow(x, t, 0, y-t, color='k', alpha=0.3, width=txt_width*0.02,
                       head_width=txt_width*0.2, head_length=txt_height*0.3,
                       zorder=0, length_includes_head=True)


def main():
    year = 2022
    month = 3
    # day = 10
    for day in range(20, 21):
        data = Dataset(datetime.date(year, month, day))
        data.plot()


if __name__ == '__main__':
    main()
