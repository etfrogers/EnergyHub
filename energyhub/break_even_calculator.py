from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

from energyhub.config import config
from solaredge import SolarEdgeClient


def main():
    se = SolarEdgeClient(config.data['solar-edge']['api-key'],
                         config.data['solar-edge']['site-id'])
    meters = se.get_energy_details(datetime(2022, 4, 1), datetime(2023, 3, 31), 'WEEK')
    dates = meters.pop('timestamps')
    for name, meter in meters.items():
        plt.plot(dates, meter, label=name)
    plt.gca().xaxis.set_major_formatter(DateFormatter('%b'))
    plt.legend()

    plt.figure()
    for name, meter in meters.items():
        plt.plot(dates, np.cumsum(meter), label=name)
    plt.gca().xaxis.set_major_formatter(DateFormatter('%b'))
    plt.legend()

    plt.figure()
    plt.plot(dates,
             np.cumsum(meters['FeedIn'] - meters['Purchased']))
    plt.gca().xaxis.set_major_formatter(DateFormatter('%m'))
    plt.show()


if __name__ == '__main__':
    main()
