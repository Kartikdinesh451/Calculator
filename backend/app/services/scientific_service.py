"""Scientific calculator: everything in the basic calculator plus functions."""

from app.services.expression_engine import CalculationError, evaluate

__all__ = ["calculate_scientific", "CalculationError"]


def calculate_scientific(expression: str, is_degree: bool = True) -> str:
    """
    Evaluate a scientific expression and return the answer as a string.

    Functions : sin cos tan asin acos atan log(base 10) ln sqrt cbrt abs exp
    Constants : pi (or π), e
    Operators : + - * / % ^ ! ( )  - implicit multiplication such as 2π or 3(4+5) works
    ``is_degree`` selects degrees (True) or radians (False) for the trig functions
    (and for the *result* of asin/acos/atan).
    """
    return evaluate(expression, scientific=True, degrees=is_degree)
