import logging

from fastapi import APIRouter, HTTPException

from app.models.database import add_history
from app.models.schemas import CalculateRequest, CalculateResponse
from app.services.calculator_service import CalculationError, calculate_basic

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/calculate", response_model=CalculateResponse)
def calculate(request: CalculateRequest):
    """Calculate a basic mathematical expression."""
    try:
        result = calculate_basic(request.expression)
    except CalculationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        add_history(request.expression, result, "basic")
    except Exception:  # a history problem must never break a calculation
        logger.exception("Could not save history")
    return CalculateResponse(result=result, expression=request.expression)
