import datetime
import zoneinfo

import numpy as np
import pytest

from ..bill_estimator import BillEstimator, MissingMeterReadingError
from ..config import config


test_days = [datetime.date(2022, 11, 25),
             datetime.date(2022, 3, 7),
             datetime.date(2023, 2, 14),
             datetime.date(2023, 4, 4),
             datetime.date(2023, 4, 3),
             datetime.date(2023, 4, 2),
             datetime.date(2023, 4, 1),
             ]


@pytest.mark.parametrize('day', test_days)
def test_consumption_equivalence(day):
    est = BillEstimator()
    se_consumption = est.estimate_consumption_from_solar_edge(day)
    try:
        octopus_consumption = est.get_consumption_for_day(day)
    except MissingMeterReadingError as err:
        pytest.xfail(str(err))
    # noinspection PyUnboundLocalVariable
    assert np.isclose(sum(se_consumption), sum(octopus_consumption), rtol=0.01, atol=0.2)
    assert np.allclose(se_consumption, octopus_consumption, atol=0.75)


@pytest.mark.parametrize('day', test_days)
def test_export_equivalence(day):
    est = BillEstimator()
    se_export = est.estimate_export_from_solar_edge(day)
    try:
        octopus_export = est.get_export_for_day(day)
    except MissingMeterReadingError as err:
        pytest.xfail(str(err))
    # noinspection PyUnboundLocalVariable
    assert np.isclose(sum(se_export), sum(octopus_export), rtol=0.01, atol=0.35)
    assert np.allclose(se_export, octopus_export, atol=0.3)


@pytest.mark.parametrize('day', test_days)
@pytest.mark.parametrize('inc_vat', [True, False])
def test_estimate_vs_calculation(day, inc_vat):
    est = BillEstimator()
    se_bill = est.estimate_bill_for_day(day, inc_vat)
    try:
        octopus_bill = est.calculate_bill_for_day(day, inc_vat)
    except MissingMeterReadingError as err:
        pytest.xfail(str(err))
    # noinspection PyUnboundLocalVariable
    bill_difference = (octopus_bill - se_bill)
    bill_percent_error = 100 * bill_difference / octopus_bill
    print(f'Bill error £{bill_difference/100:.2f} ({bill_percent_error:.0f}%)')
    assert np.isclose(se_bill, octopus_bill, atol=2, rtol=0.03)
