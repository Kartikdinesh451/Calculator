from fastapi import APIRouter, Query

from app.models.database import clear_history, get_history
from app.models.schemas import HistoryResponse

router = APIRouter()


@router.get("/", response_model=HistoryResponse)
def read_history(limit: int = Query(50, ge=1, le=500)):
    """Get calculation history (newest first)."""
    return HistoryResponse(history=get_history(limit))


@router.delete("/")
def delete_history():
    """Clear all calculation history."""
    clear_history()
    return {"message": "History cleared successfully"}
