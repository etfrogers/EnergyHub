import datetime

import numpy as np
import pytest

from ..bill_estimator import BillEstimator, MissingMeterReadingError


test_days = [datetime.date(2022, 11, 25),
             datetime.date(2022, 3, 7),
             datetime.date(2023, 2, 14),
             datetime.date(2023, 4, 4),
             datetime.date(2023, 4, 3),
             datetime.date(2023, 4, 2),
             datetime.date(2023, 4, 1),
             ]

real_bills = [  # prices exc VAT
    # date, total consumption, price (£)
    (datetime.date(2022, 12, 2), 17.57, 5.73),
    (datetime.date(2022, 12, 1), 76.53, 24.95),
    (datetime.date(2022, 11, 30), 31.60, 10.30),
    (datetime.date(2022, 11, 29), 25.20, 8.21),
    (datetime.date(2022, 11, 28), 7.95, 2.56),
    (datetime.date(2022, 11, 27), 52.02, 9.55),
]

real_export = [  # prices exc VAT
    # date, total export, credit (£)
    (datetime.date(2021, 8, 22), 31.66, 4.13),
    (datetime.date(2021, 8, 23), 17.08, 2.53),
    (datetime.date(2021, 8, 24), 37.84, 5.16),
    (datetime.date(2021, 8, 25), 40.91, 5.66),
    (datetime.date(2021, 8, 26), 38.22, 4.69),
    (datetime.date(2021, 8, 27), 18.08, 2.37),
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


@pytest.mark.parametrize('day, actual_consumption, actual_price', real_bills)
def test_api_against_bills(day, actual_consumption, actual_price):
    est = BillEstimator()
    api_consumption = est.get_consumption_for_day(day)
    calculated_bill = est.calculate_bill_for_day(day, inc_vat=False)
    # only matches dues to more than 0.01 due to different rounding?
    assert np.isclose(sum(api_consumption), actual_consumption, atol=0.05)
    # actual price in £, calculation in pence. Should match to the nearest penny, but
    # allow 2p, due to rounding one value in one direction, one in the other
    assert np.isclose(calculated_bill, actual_price*100, atol=2)


@pytest.mark.parametrize('day, actual_consumption, actual_price', real_bills)
def test_solaredge_estimate_against_bills(day, actual_consumption, actual_price):
    est = BillEstimator()
    estimated_consumption = est.estimate_consumption_from_solar_edge(day)
    estimated_bill = est.estimate_bill_for_day(day, inc_vat=False)
    # match to 0.1 kWh?
    assert np.isclose(sum(estimated_consumption), actual_consumption, atol=0.1, rtol=0.05)
    # actual price in £, calculation in pence. Should match to within 11p
    assert np.isclose(estimated_bill, actual_price*100, atol=11)


@pytest.mark.parametrize('day, actual_export, actual_credit', real_export)
def test_api_export_against_bills(day, actual_export, actual_credit):
    est = BillEstimator()
    api_export = est.get_export_for_day(day)
    calculated_credit = est.calculate_credit_for_day(day, inc_vat=False)
    # only matches dues to more than 0.01 due to different rounding?
    assert np.isclose(sum(api_export), actual_export, atol=0.15)
    # actual price in £, calculation in pence. Should match to the nearest penny, but
    # allow 2p, due to rounding one value in one direction, one in the other
    assert np.isclose(calculated_credit, actual_credit * 100, atol=2)


@pytest.mark.parametrize('day, actual_export, actual_credit', real_export)
def test_solaredge_export_estimate_against_bills(day, actual_export, actual_credit):
    est = BillEstimator()
    estimated_export = est.estimate_export_from_solar_edge(day)
    estimated_credit = est.estimate_credit_for_day(day, inc_vat=False)
    # match to 0.1 kWh or 5%
    assert np.isclose(sum(estimated_export), actual_export, atol=0.1, rtol=0.05)
    # actual price in £, calculation in pence. Should match to within 11p
    assert np.isclose(estimated_credit, actual_credit*100, atol=11)
