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

    # 5 minute intervals, means 12 to an hour, so one 1kW at one point is 1/12 kWh
    @property
    def total_consumption(self):
        return np.sum(self.consumption) / 12

    @property
    def total_heating(self):
        return np.sum(self.heating) / 12

    @property
    def cop(self):
        return self.heating / self.consumption

    @property
    def daily_cop(self):
        return np.nanmean(self.cop)

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
        ax1.legend()
        ax2.legend(loc='upper left')
        plt.suptitle(f'{self.date_str}')
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


def main():
    year = 2022
    month = 3
    # day = 10
    for day in range(10, 17):
        data = Dataset(datetime.date(year, month, day))
        data.plot()


if __name__ == '__main__':
    main()
