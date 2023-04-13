from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

from energyhub.config import config
from solaredge import SolarEdgeClient
from solaredge.solar_edge_api import API_TIME_FORMAT


def main():
    se = SolarEdgeClient(config.data['solar-edge']['api-key'],
                         config.data['solar-edge']['site-id'])
    details = se.get_energy_details(datetime(2022, 4, 1), datetime(2023, 3, 31), 'WEEK')
    details = details['energyDetails']
    assert details['timeUnit'] == 'WEEK'
    meters = details['meters']
    new_meters = {}
    for meter in meters:
        values = meter['values']
        dates = [datetime.strptime(v['date'], API_TIME_FORMAT) for v in values]
        energies = [v.get('value', np.nan) for v in values]
        new_meters[meter['type']] = {'dates': np.array(dates),
                                     'energies': np.array(energies)/1000,
                                     }
    for name, meter in new_meters.items():
        plt.plot(meter['dates'], meter['energies'], label=name)
    plt.gca().xaxis.set_major_formatter(DateFormatter('%b'))
    plt.legend()

    plt.figure()
    for name, meter in new_meters.items():
        plt.plot(meter['dates'], np.cumsum(meter['energies']), label=name)
    plt.gca().xaxis.set_major_formatter(DateFormatter('%b'))
    plt.legend()

    plt.figure()
    plt.plot(new_meters['Purchased']['dates'],
             np.cumsum(new_meters['FeedIn']['energies']-new_meters['Purchased']['energies']))
    plt.gca().xaxis.set_major_formatter(DateFormatter('%m'))
    plt.show()


if __name__ == '__main__':
    main()
