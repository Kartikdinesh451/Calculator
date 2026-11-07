"""Basic calculator: + - * / % and parentheses."""

from app.services.expression_engine import CalculationError, evaluate

__all__ = ["calculate_basic", "CalculationError"]


def calculate_basic(expression: str) -> str:
    """
    Evaluate a basic arithmetic expression and return the answer as a string.

    The answer is a string (not a float) so large whole numbers and long decimals
    reach the browser exactly as calculated.

    Supports: + - * / % ( ) and decimals.  ``%`` is the remainder (modulo)
    operator, e.g. ``17 % 5 = 2``.
    """
    return evaluate(expression, scientific=False)
