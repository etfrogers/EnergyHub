import datetime

import requests
import numpy as np
import matplotlib.pyplot as plt


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
        self._full_data = self.process_file_data(contents)

        # indices taken from Javascript plotting code
        # (need to subtract 2 from the indices used there to allow for serial and timestamp)
        self.consumption = self._full_data[:, 24] / 10
        self.heating = self._full_data[:, 25] / 10

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
            ax1 = plt.subplot(1, 1, 1)
            ax2 = ax1.twinx()
        else:
            ax1, ax2 = axes
        ax1.plot(self.consumption, label=f'Electrical power: {self.total_consumption:.2f} kWh', color='red')
        ax1.plot(self.heating, label=f'Heating power: {self.total_heating:.2f} kWh', color='lightgreen')
        ax1.set_ylabel('kW')
        ax2.plot(self.cop, label=f'Mean COP: {self.daily_cop:.2f}')
        ax1.legend(loc='upper right')
        ax2.legend(loc='upper left')
        plt.suptitle(f'{self.date_str}')

        x_data = []
        y_data = []
        labels = []
        for chunk in self.chunks():
            chunk_inds = range(chunk[0], chunk[1]+1)
            chunk_heating = self.heating[chunk_inds]
            chunk_consumption = self.consumption[chunk_inds]
            chunk_cop = self.cop[chunk_inds]
            assert not np.any(np.isnan(chunk_cop))
            x_data.append(chunk[0])
            y_data.append(np.max(chunk_heating)+0.1)
            label = (f'{self.total_power(chunk_consumption):.1f} kWh\n'
                     + f'PF: {np.mean(chunk_cop):.2f}')
            labels.append(label)
            # ax1.text(chunk[0], np.max(chunk_heating)+0.1,
            #          f'{self.total_power(chunk_consumption):.1f} kWh\n'
            #          f'PF: {np.mean(chunk_cop):.2f}')
        txt_height = 0.07 * (ax1.get_ylim()[1] - ax1.get_ylim()[0])
        txt_width = 0.12 * (ax1.get_xlim()[1] - ax1.get_xlim()[0])
        # Get the corrected text positions, then write the text.
        text_positions = get_text_positions(x_data, y_data, txt_width, txt_height)
        text_plotter(x_data, y_data, labels, text_positions, ax1, txt_width, txt_height)

        plt.show()
        return [ax1, ax2]

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
                timestamps.append(timestamp)
                data.append([float(val) for val in entry])
        data = np.array(data)
        return data


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
    for day in range(15, 16):
        data = Dataset(datetime.date(year, month, day))
        data.plot()


if __name__ == '__main__':
    main()
