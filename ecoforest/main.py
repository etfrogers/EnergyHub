import requests
import numpy as np
import matplotlib.pyplot as plt


def main():
    year = 2022
    month = 3
    day = 12
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
    filtered_data = []
    new_col = 0
    for col in range(data.shape[1]):  # drop columns with all zeros (or sentinel) values
        column = data[:, col]
        if not (np.all(column == 0) or np.all(column == -9999)):
            filtered_data.append(column)
            new_col += 1
    filtered_data = np.array(filtered_data).transpose()
    # filtered_data[filtered_data == -9999] = np.nan
    filtered_data = filtered_data / 10  # this appears to be the conversion used in the javascript file

    # taken from Javascript plotting code
    # (need to subtract 2 from the indices used there to allow for serial and timestamp)
    consumption = data[:, 24] / 10
    heating = data[:, 25] / 10
    cop = heating / consumption
    daily_cop = np.nanmean(cop)
    ax1 = plt.subplot(1, 1, 1)
    ax1.plot(consumption, label='Electrical power', color='red')
    ax1.plot(heating, label='Heating power', color='lightgreen')
    ax1.set_ylabel('kW')
    ax2 = ax1.twinx()
    ax2.plot(cop, label=f'Mean COP: {daily_cop:.2f}')
    ax1.legend()
    ax2.legend(loc='upper left')
    plt.show()


if __name__ == '__main__':
    main()
