import requests
import numpy as np
import matplotlib.pyplot as plt


class Dataset:
    def __init__(self, day: int, month: int, year: int):
        self.day = day
        self.month = month
        self.year = year
        use_cache = True
        if use_cache:
            try:
                with open(f'data/{year}-{month:02d}-{day}.csv') as file:
                    contents = file.read()
            except FileNotFoundError:
                contents = self.get_data_from_server(day, month, year)
                # TODO do not cache today's data
                with open(f'data/{year}-{month:02d}-{day}.csv', 'w') as file:
                    file.write(contents)
        else:
            contents = self.get_data_from_server(day, month, year)
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

    def plot(self):
        ax1 = plt.subplot(1, 1, 1)
        ax1.plot(self.consumption, label=f'Electrical power: {self.total_consumption:.2f} kWh', color='red')
        ax1.plot(self.heating, label=f'Heating power: {self.total_heating:.2f} kWh', color='lightgreen')
        ax1.set_ylabel('kW')
        ax2 = ax1.twinx()
        ax2.plot(self.cop, label=f'Mean COP: {self.daily_cop:.2f}')
        ax1.legend()
        ax2.legend(loc='upper left')
        plt.suptitle(f'{self.day}/{self.month}/{self.year}')
        plt.show()

    @staticmethod
    def get_data_from_server(day, month, year):
        server = '192.168.1.147'
        port = '8000'
        data_dir = 'historic'
        serial = '**REMOVED**'
        filename = f'{year}-{month:02d}-{day}_{serial}_1_historico.csv'
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
        data = Dataset(day, month, year)
        data.plot()


if __name__ == '__main__':
    main()
