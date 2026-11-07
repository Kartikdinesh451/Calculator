import pytest

from app.services.expression_engine import CalculationError
from app.services.financial_service import (
    calculate_emi, calculate_interest, calculate_mortgage, calculate_roi,
)


def test_emi_matches_independent_formula():
    result = calculate_emi(10000, 5, 36)
    P, r, n = 10000, 0.05 / 12, 36
    expected = P * r * (1 + r) ** n / ((1 + r) ** n - 1)
    assert result["emi"] == pytest.approx(expected, abs=0.005)
    assert result["emi"] == 299.71
    assert result["total_payment"] == pytest.approx(expected * n, abs=0.01)
    assert result["total_interest"] == pytest.approx(expected * n - P, abs=0.01)


def test_emi_zero_rate():
    assert calculate_emi(10000, 0, 12) == {"emi": 833.33, "total_payment": 10000.0, "total_interest": 0.0}


def test_emi_rejects_bad_input():
    for args in [(0, 5, 12), (-1, 5, 12), (1000, -1, 12), (1000, 5, 0), (1000, 5, 36.5), (1000, 5, 1201),
                 (float("nan"), 5, 12), (1000, 5001, 12)]:
        with pytest.raises(CalculationError):
            calculate_emi(*args)


def test_simple_and_compound_interest():
    assert calculate_interest(10000, 5, 5, "simple") == {"interest": 2500.0, "total_amount": 12500.0}
    assert calculate_interest(10000, 5, 5, "compound") == {"interest": 2762.82, "total_amount": 12762.82}
    # 12% compounded monthly for 1 year = 12.6825%
    assert calculate_interest(10000, 12, 1, "compound", 12) == {"interest": 1268.25, "total_amount": 11268.25}
    # fractional years
    assert calculate_interest(1000, 10, 0.5, "simple")["interest"] == 50.0
    assert calculate_interest(1000, 10, 2.5, "compound")["total_amount"] == pytest.approx(1000 * 1.1 ** 2.5, abs=0.005)


def test_interest_validation():
    with pytest.raises(CalculationError):
        calculate_interest(1000, 5, 1, "weird")
    with pytest.raises(CalculationError):
        calculate_interest(1000, 5, 0, "simple")
    with pytest.raises(CalculationError):
        calculate_interest(1000, 5, 1, "compound", 7)
    with pytest.raises(CalculationError):          # result too big for a JSON float
        calculate_interest(1e12, 1000, 1000, "compound", 365)


def test_mortgage():
    result = calculate_mortgage(300000, 60000, 4.5, 30)
    P, r, n = 240000, 0.045 / 12, 360
    expected = P * r * (1 + r) ** n / ((1 + r) ** n - 1)
    assert result["loan_amount"] == 240000.0
    assert result["monthly_payment"] == pytest.approx(expected, abs=0.005)
    assert result["monthly_payment"] == 1216.04
    assert result["total_interest"] == pytest.approx(expected * n - P, abs=0.01)


def test_mortgage_validation():
    with pytest.raises(CalculationError):
        calculate_mortgage(100000, 100000, 5, 10)    # old code divided by zero / went negative
    with pytest.raises(CalculationError):
        calculate_mortgage(100000, 150000, 5, 10)
    with pytest.raises(CalculationError):
        calculate_mortgage(100000, 0, 5, 0)
    assert calculate_mortgage(120000, 0, 0, 10)["monthly_payment"] == 1000.0


def test_roi():
    assert calculate_roi(10000, 15000) == {"profit": 5000.0, "roi_percentage": 50.0}
    assert calculate_roi(3, 2) == {"profit": -1.0, "roi_percentage": -33.33}
    assert calculate_roi(100, 0) == {"profit": -100.0, "roi_percentage": -100.0}
    with pytest.raises(CalculationError):
        calculate_roi(0, 10)


def test_half_up_rounding_not_bankers():
    # 0.125 -> 0.13 (half-up); float/round() would give 0.12
    assert calculate_interest(12.5, 1, 1, "simple")["interest"] == 0.13
