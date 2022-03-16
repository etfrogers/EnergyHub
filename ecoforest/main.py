import requests
import numpy as np
import matplotlib.pyplot as plt


def main():
    year = 2022
    month = 3
    day = 15
    data = get_data_from_server(day, month, year)

    # taken from Javascript plotting code
    # (need to subtract 2 from the indices used there to allow for serial and timestamp)
    consumption = data[:, 24] / 10
    heating = data[:, 25] / 10

    # 5 minute intervals, means 12 to an hour, so one 1kW at one point is 1/12 kWh
    total_consumption = np.sum(consumption) / 12
    total_heating = np.sum(heating) / 12
    cop = heating / consumption
    daily_cop = np.nanmean(cop)

    ax1 = plt.subplot(1, 1, 1)
    ax1.plot(consumption, label=f'Electrical power: {total_consumption:.2f} kWh', color='red')
    ax1.plot(heating, label=f'Heating power: {total_heating:.2f} kWh', color='lightgreen')
    ax1.set_ylabel('kW')
    ax2 = ax1.twinx()
    ax2.plot(cop, label=f'Mean COP: {daily_cop:.2f}')
    ax1.legend()
    ax2.legend(loc='upper left')
    plt.suptitle(f'{day}/{month}/{year}')
    plt.show()


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
    contents = response.text
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


if __name__ == '__main__':
    main()
