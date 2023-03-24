import datetime

import numpy as np
import pytest
from matplotlib import pyplot as plt

from ..bill_estimator import BillEstimator
from ..config import config
from octopus_client.octopy.octopus_api import OctopusClient


@pytest.mark.parametrize('day', [datetime.date(2023, 4, 3)])
def test_consumption_equivalence(day):
    est = BillEstimator()
    se_consumption = est.estimate_consumption_from_solar_edge(day)
    octopus_consumption = est.get_consumption_for_day(day)
    # Solar Edge in Wh, Octopus in kWh
    se_consumption /= 1000
    assert np.isclose(sum(se_consumption), sum(octopus_consumption), rtol=0.01, atol=0.2)
    assert np.allclose(se_consumption, octopus_consumption, atol=0.3)


@pytest.mark.parametrize('day', [datetime.date(2023, 4, 4),
                                 datetime.date(2023, 4, 3),
                                 datetime.date(2023, 4, 2),
                                 datetime.date(2023, 4, 1),
                                 ])
def test_export_equivalence(day):
    est = BillEstimator()
    se_export = est.estimate_export_from_solar_edge(day)
    octopus_export = est.get_export_for_day(day)
    # Solar Edge in Wh, Octopus in kWh
    se_export /= 1000
    assert np.isclose(sum(se_export), sum(octopus_export), rtol=0.01, atol=0.2)
    assert np.allclose(se_export, octopus_export, atol=0.3)
