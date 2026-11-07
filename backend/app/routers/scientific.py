import logging

from fastapi import APIRouter, HTTPException

from app.models.database import add_history
from app.models.schemas import ScientificCalculateRequest, ScientificCalculateResponse
from app.services.scientific_service import CalculationError, calculate_scientific

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/calculate", response_model=ScientificCalculateResponse)
def calculate(request: ScientificCalculateRequest):
    """Calculate a scientific mathematical expression."""
    try:
        result = calculate_scientific(request.expression, request.is_degree)
    except CalculationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        unit = "deg" if request.is_degree else "rad"
        add_history(f"{request.expression}  [{unit}]", result, "scientific")
    except Exception:
        logger.exception("Could not save history")
    return ScientificCalculateResponse(result=result, expression=request.expression)
