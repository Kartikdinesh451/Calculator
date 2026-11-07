"""
Financial calculators (EMI, interest, mortgage, ROI).

All money maths uses ``Decimal`` and rounds half-up to 2 decimal places only at
the very end, so the results match bank / spreadsheet calculators (floats can be
off by a cent).
"""

from decimal import Context, Decimal, ROUND_HALF_UP, localcontext
from typing import Dict, Union

from app.services.expression_engine import CalculationError

Number = Union[int, float, Decimal, str]

CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("1000000000000")      # 1 trillion
MAX_RATE = Decimal("1000")                 # percent per year
MAX_LOAN_MONTHS = 1200                     # 100 years
MAX_YEARS = Decimal("1000")
MAX_OUTPUT = Decimal("1000000000000000")   # keep results inside float's exact range
VALID_COMPOUNDING = (1, 2, 4, 12, 365)

_CONTEXT = Context(prec=60)


def _d(value: Number) -> Decimal:
    """Convert to Decimal via str() so 0.1 stays 0.1 (not 0.1000000000000000055...)."""
    try:
        number = Decimal(str(value))
    except Exception:
        raise CalculationError("Please enter valid numbers")
    if not number.is_finite():
        raise CalculationError("Please enter valid numbers")
    return number


def _money(value: Decimal) -> float:
    """Round half-up to cents and return a float for JSON."""
    if abs(value) > MAX_OUTPUT:
        raise CalculationError("Result is too large to display")
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _require_amount(value: Decimal, label: str, *, allow_zero: bool = False) -> None:
    if value < 0 or (value == 0 and not allow_zero):
        raise CalculationError(f"{label} must be greater than 0" if not allow_zero
                               else f"{label} cannot be negative")
    if value > MAX_AMOUNT:
        raise CalculationError(f"{label} is too large")


def _require_rate(rate: Decimal) -> None:
    if rate < 0:
        raise CalculationError("Interest rate cannot be negative")
    if rate > MAX_RATE:
        raise CalculationError(f"Interest rate cannot be more than {MAX_RATE}%")


def _installment(principal: Decimal, annual_rate_percent: Decimal, months: int) -> Decimal:
    """Standard amortisation formula: P*r*(1+r)^n / ((1+r)^n - 1); P/n when rate is 0."""
    with localcontext(_CONTEXT):
        if annual_rate_percent == 0:
            return principal / months
        r = annual_rate_percent / 100 / 12
        growth = (1 + r) ** months
        return principal * r * growth / (growth - 1)


def calculate_emi(principal: Number, rate: Number, term: int) -> Dict[str, float]:
    """
    EMI (Equated Monthly Instalment).

    principal : loan amount
    rate      : annual interest rate in percent (0 is allowed)
    term      : loan term in whole months
    """
    principal_d, rate_d = _d(principal), _d(rate)
    _require_amount(principal_d, "Loan amount")
    _require_rate(rate_d)
    if int(term) != term or not 1 <= term <= MAX_LOAN_MONTHS:
        raise CalculationError(f"Loan term must be a whole number of months from 1 to {MAX_LOAN_MONTHS}")
    months = int(term)

    emi = _installment(principal_d, rate_d, months)
    total_payment = emi * months
    return {
        "emi": _money(emi),
        "total_payment": _money(total_payment),
        "total_interest": _money(total_payment - principal_d),
    }


def calculate_interest(
    principal: Number,
    rate: Number,
    time: Number,
    interest_type: str,
    compounds_per_year: int = 1,
) -> Dict[str, float]:
    """
    Simple or compound interest.

    time               : years (may be fractional, e.g. 2.5)
    interest_type      : 'simple' or 'compound'
    compounds_per_year : 1, 2, 4, 12 or 365 (only used for compound interest)
    """
    principal_d, rate_d, time_d = _d(principal), _d(rate), _d(time)
    _require_amount(principal_d, "Principal")
    _require_rate(rate_d)
    if time_d <= 0 or time_d > MAX_YEARS:
        raise CalculationError(f"Time must be greater than 0 and at most {MAX_YEARS} years")

    kind = str(interest_type).lower()
    if kind not in ("simple", "compound"):
        raise CalculationError("Interest type must be 'simple' or 'compound'")
    if compounds_per_year not in VALID_COMPOUNDING:
        raise CalculationError("Compounding must be 1, 2, 4, 12 or 365 times per year")

    with localcontext(_CONTEXT):
        r = rate_d / 100
        if kind == "simple":
            interest = principal_d * r * time_d
            total = principal_d + interest
        else:
            n = Decimal(compounds_per_year)
            total = principal_d * (1 + r / n) ** (n * time_d)
            interest = total - principal_d
    return {"interest": _money(interest), "total_amount": _money(total)}


def calculate_mortgage(price: Number, down_payment: Number, rate: Number, term: int) -> Dict[str, float]:
    """
    Mortgage monthly payment.

    price        : home price
    down_payment : paid up-front (must be less than the price)
    rate         : annual interest rate in percent
    term         : loan term in whole years
    """
    price_d, down_d, rate_d = _d(price), _d(down_payment), _d(rate)
    _require_amount(price_d, "Home price")
    _require_amount(down_d, "Down payment", allow_zero=True)
    _require_rate(rate_d)
    if int(term) != term or not 1 <= term * 12 <= MAX_LOAN_MONTHS:
        raise CalculationError(f"Loan term must be a whole number of years from 1 to {MAX_LOAN_MONTHS // 12}")
    if down_d >= price_d:
        raise CalculationError("Down payment must be less than the home price")

    loan = price_d - down_d
    months = int(term) * 12
    monthly = _installment(loan, rate_d, months)
    total_payment = monthly * months
    return {
        "loan_amount": _money(loan),
        "monthly_payment": _money(monthly),
        "total_payment": _money(total_payment),
        "total_interest": _money(total_payment - loan),
    }


def calculate_roi(initial_investment: Number, final_value: Number) -> Dict[str, float]:
    """Return on investment: profit and ROI percentage."""
    initial, final = _d(initial_investment), _d(final_value)
    _require_amount(initial, "Initial investment")
    _require_amount(final, "Final value", allow_zero=True)

    profit = final - initial
    with localcontext(_CONTEXT):
        roi = profit / initial * 100
    return {"profit": _money(profit), "roi_percentage": _money(roi)}
