from typing import List, Literal

from pydantic import BaseModel, Field

# ---- Basic / scientific ----------------------------------------------------
class CalculateRequest(BaseModel):
    expression: str = Field(..., min_length=1, max_length=500, description="Mathematical expression to evaluate")


class CalculateResponse(BaseModel):
    # A string, not a float: keeps big integers and long decimals exact.
    result: str
    expression: str


class ScientificCalculateRequest(BaseModel):
    expression: str = Field(..., min_length=1, max_length=500, description="Scientific expression to evaluate")
    is_degree: bool = Field(True, description="Use degrees (True) or radians (False)")


class ScientificCalculateResponse(BaseModel):
    result: str
    expression: str


# ---- Financial -------------------------------------------------------------
_AMOUNT = dict(gt=0, le=1e12, allow_inf_nan=False)
_RATE = dict(ge=0, le=1000, allow_inf_nan=False)


class LoanRequest(BaseModel):
    principal: float = Field(..., description="Loan amount", **_AMOUNT)
    rate: float = Field(..., description="Annual interest rate in percent (0 allowed)", **_RATE)
    term: int = Field(..., ge=1, le=1200, description="Loan term in months")


class LoanResponse(BaseModel):
    emi: float
    total_payment: float
    total_interest: float


class InterestRequest(BaseModel):
    principal: float = Field(..., description="Principal amount", **_AMOUNT)
    rate: float = Field(..., description="Annual interest rate in percent", **_RATE)
    time: float = Field(..., gt=0, le=1000, allow_inf_nan=False, description="Time period in years")
    type: Literal["simple", "compound"] = Field("simple", description="'simple' or 'compound'")
    compounds_per_year: Literal[1, 2, 4, 12, 365] = Field(1, description="Compounding frequency (compound only)")


class InterestResponse(BaseModel):
    interest: float
    total_amount: float


class MortgageRequest(BaseModel):
    price: float = Field(..., description="Home price", **_AMOUNT)
    down_payment: float = Field(..., ge=0, le=1e12, allow_inf_nan=False, description="Down payment amount")
    rate: float = Field(..., description="Annual interest rate in percent", **_RATE)
    term: int = Field(..., ge=1, le=100, description="Loan term in years")


class MortgageResponse(BaseModel):
    loan_amount: float
    monthly_payment: float
    total_payment: float
    total_interest: float


class ROIRequest(BaseModel):
    initial_investment: float = Field(..., description="Initial investment amount", **_AMOUNT)
    final_value: float = Field(..., ge=0, le=1e12, allow_inf_nan=False, description="Final value of investment")


class ROIResponse(BaseModel):
    profit: float
    roi_percentage: float


# ---- History ---------------------------------------------------------------
class HistoryItem(BaseModel):
    id: int
    expression: str
    result: str
    timestamp: str
    calculator_type: str


class HistoryResponse(BaseModel):
    history: List[HistoryItem]
