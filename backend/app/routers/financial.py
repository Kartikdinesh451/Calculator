import logging

from fastapi import APIRouter, HTTPException

from app.models.database import add_history
from app.models.schemas import (
    InterestRequest, InterestResponse,
    LoanRequest, LoanResponse,
    MortgageRequest, MortgageResponse,
    ROIRequest, ROIResponse,
)
from app.services.expression_engine import CalculationError
from app.services.financial_service import (
    calculate_emi, calculate_interest, calculate_mortgage, calculate_roi,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _money(x: float) -> str:
    return f"${x:,.2f}"


def _save(expression: str, result: str) -> None:
    try:
        add_history(expression, result, "financial")
    except Exception:
        logger.exception("Could not save history")


@router.post("/loan", response_model=LoanResponse)
def loan(request: LoanRequest):
    """Calculate EMI for a loan."""
    try:
        result = calculate_emi(request.principal, request.rate, request.term)
    except CalculationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _save(f"Loan: {_money(request.principal)} at {request.rate}% for {request.term} months",
          f"EMI: {_money(result['emi'])}")
    return LoanResponse(**result)


@router.post("/interest", response_model=InterestResponse)
def interest(request: InterestRequest):
    """Calculate simple or compound interest."""
    try:
        result = calculate_interest(
            request.principal, request.rate, request.time, request.type, request.compounds_per_year
        )
    except CalculationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _save(f"{request.type.capitalize()} interest: {_money(request.principal)} at {request.rate}% "
          f"for {request.time} years",
          f"Interest: {_money(result['interest'])}")
    return InterestResponse(**result)


@router.post("/mortgage", response_model=MortgageResponse)
def mortgage(request: MortgageRequest):
    """Calculate mortgage monthly payment."""
    try:
        result = calculate_mortgage(request.price, request.down_payment, request.rate, request.term)
    except CalculationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _save(f"Mortgage: {_money(request.price)} with {_money(request.down_payment)} down at "
          f"{request.rate}% for {request.term} years",
          f"Monthly: {_money(result['monthly_payment'])}")
    return MortgageResponse(**result)


@router.post("/roi", response_model=ROIResponse)
def roi(request: ROIRequest):
    """Calculate return on investment."""
    try:
        result = calculate_roi(request.initial_investment, request.final_value)
    except CalculationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _save(f"ROI: invested {_money(request.initial_investment)}, final {_money(request.final_value)}",
          f"ROI: {result['roi_percentage']:,.2f}%")
    return ROIResponse(**result)
