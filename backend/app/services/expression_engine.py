"""
Safe expression engine used by the basic and scientific calculators.

Why this exists
---------------
The original code ran ``eval()`` on user input and used binary floats.  That
gave wrong answers (0.00001*2 -> 0.0, sin(30) -> SyntaxError, abs() crashed,
"07+1" crashed), lost precision on big integers, and let a request such as
``9**9**9**9`` hang the server.

This module instead:

* tokenises and parses the text itself (recursive descent) - nothing is ever
  passed to ``eval``/``exec``;
* does all arithmetic with ``decimal.Decimal`` (60 digits), so 0.1 + 0.2 is
  exactly 0.3 and 12345678901234567890 + 1 is exact;
* rounds only once, at the very end, to 15 significant digits (what a
  hand-held calculator effectively does).

Grammar (lowest to highest precedence)::

    expr     := term (('+' | '-') term)*
    term     := unary (('*' | '/' | '%') unary | implicit-multiply)*
    unary    := ('+' | '-') unary | power
    power    := postfix ('^' signed_power)?          (right associative)
    postfix  := primary '!'*
    primary  := NUMBER | CONSTANT | FUNCTION '(' expr ')' | '(' expr ')'

So ``-2^2 = -4``, ``2^3^2 = 512``, ``2^-1 = 0.5``, ``2pi`` and ``3(4+5)`` work.
"""

from __future__ import annotations

import math
import re
from decimal import (
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    ROUND_HALF_EVEN,
    localcontext,
)
from typing import List, Tuple

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
WORKING_PRECISION = 60      # digits used while calculating
INEXACT_PRECISION = 25      # digits kept from ln/exp/roots (they are not exact anyway)
DISPLAY_DIGITS = 15         # significant digits in the final answer
MAX_EXPRESSION_LENGTH = 500
MAX_NESTING = 60
MAX_RESULT_DIGITS = 5000    # refuse x^y results with more digits than this
MAX_FACTORIAL = 1000
MAX_EXACT_INTEGER_DIGITS = 30   # integers up to this many digits are shown in full


class CalculationError(ValueError):
    """Raised for any problem with the user's expression (bad syntax, domain error...)."""


# --------------------------------------------------------------------------- #
# Tokenizer
# --------------------------------------------------------------------------- #
_TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<num>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)   # 12  1.5  .5  1e5  2.5E-3
      | (?P<name>π|[A-Za-z]+)                           # sin  pi  e  π
      | (?P<op>\*\*|[-+*/%^!(),])                       # operators / punctuation
    )
    """,
    re.VERBOSE,
)

_SYMBOL_MAP = {
    "×": "*", "✕": "*", "·": "*",
    "÷": "/",
    "−": "-", "–": "-", "—": "-",
    "√": "sqrt",
}

FUNCTIONS = {
    "sin", "cos", "tan", "asin", "acos", "atan",
    "log", "ln", "sqrt", "cbrt", "abs", "exp",
}
CONSTANTS = {"pi", "π", "e"}

Token = Tuple[str, str]  # (kind, text) - kind in NUM, NAME, OP, END


def _tokenize(text: str) -> List[Token]:
    for symbol, replacement in _SYMBOL_MAP.items():
        text = text.replace(symbol, replacement)

    tokens: List[Token] = []
    pos = 0
    length = len(text)
    while pos < length:
        if text[pos:].strip() == "":
            break
        match = _TOKEN_RE.match(text, pos)
        if not match:
            bad = text[pos:].lstrip()[0]
            raise CalculationError(f"Unexpected character '{bad}'")
        pos = match.end()
        if match.group("num") is not None:
            tokens.append(("NUM", match.group("num")))
        elif match.group("name") is not None:
            tokens.append(("NAME", match.group("name").lower()))
        else:
            op = match.group("op")
            tokens.append(("OP", "^" if op == "**" else op))
    tokens.append(("END", ""))
    return tokens


# --------------------------------------------------------------------------- #
# Number helpers
# --------------------------------------------------------------------------- #
_PI = Decimal("3.14159265358979323846264338327950288419716939937510582097494459")
_E = Decimal("2.71828182845904523536028747135266249775724709369995957496696763")


def _clean_inexact(value: Decimal) -> Decimal:
    """Trim the meaningless trailing digits of an inexact result (ln, exp, roots...)."""
    return Context(prec=INEXACT_PRECISION, rounding=ROUND_HALF_EVEN).plus(value)


_CONST_CTX = Context(prec=WORKING_PRECISION + 10)   # module-level maths must not use the default 28 digits
_HALF_PI = _CONST_CTX.divide(_PI, 2)
_TWO_PI = _CONST_CTX.multiply(_PI, 2)
_SERIES_EPSILON = Decimal(10) ** -(WORKING_PRECISION + 5)
_ZERO_NOISE = Decimal(10) ** -40     # anything smaller after a trig call is rounding noise


def _sin_cos(x: Decimal) -> Tuple[Decimal, Decimal]:
    """sin and cos of ``x`` radians to ~60 digits (Taylor series after range reduction)."""
    x = x % _TWO_PI
    if x > _PI:
        x -= _TWO_PI
    elif x < -_PI:
        x += _TWO_PI
    x2 = x * x

    sin_total, term, n = x, x, 1
    while abs(term) > _SERIES_EPSILON:
        term = -term * x2 / ((n + 1) * (n + 2))
        sin_total += term
        n += 2

    cos_total, term, n = Decimal(1), Decimal(1), 0
    while abs(term) > _SERIES_EPSILON:
        term = -term * x2 / ((n + 1) * (n + 2))
        cos_total += term
        n += 2
    return sin_total, cos_total


def _atan(x: Decimal) -> Decimal:
    """arctan to ~60 digits: float first guess, then Newton refinement in Decimal."""
    if x == 0:
        return Decimal(0)
    if abs(x) > Decimal("1e30"):
        return (_HALF_PI - 1 / x) if x > 0 else (-_HALF_PI - 1 / x)
    y = Decimal(math.atan(float(x)))
    for _ in range(4):
        s, c = _sin_cos(y)
        y = y - (s - x * c) * c
    return y


def _is_integral(value: Decimal) -> bool:
    return value == value.to_integral_value()


def _check_power_size(base: Decimal, exponent: Decimal) -> None:
    """Refuse powers whose result would be absurdly large (e.g. 9^9^9^9)."""
    if base == 0 or base == 1 or base == -1:
        return
    digits = abs(exponent) * abs(abs(base).log10())
    if digits > MAX_RESULT_DIGITS:
        raise CalculationError("Result is too large to calculate")


# --------------------------------------------------------------------------- #
# Parser / evaluator
# --------------------------------------------------------------------------- #
class _Parser:
    def __init__(self, tokens: List[Token], *, scientific: bool, degrees: bool):
        self.tokens = tokens
        self.pos = 0
        self.scientific = scientific
        self.degrees = degrees
        self.depth = 0

    # -- token helpers ------------------------------------------------------ #
    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _next(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def _is_op(self, *ops: str) -> bool:
        kind, text = self._peek()
        return kind == "OP" and text in ops

    def _enter(self) -> None:
        self.depth += 1
        if self.depth > MAX_NESTING:
            raise CalculationError("Expression is nested too deeply")

    def _leave(self) -> None:
        self.depth -= 1

    # -- grammar ------------------------------------------------------------ #
    def parse(self) -> Decimal:
        if self._peek()[0] == "END":
            raise CalculationError("Expression is empty")
        value = self._expr()
        kind, text = self._peek()
        if kind != "END":
            if text == ")":
                raise CalculationError("Mismatched parentheses: extra ')'")
            if text == ",":
                raise CalculationError("Commas are not supported")
            if kind == "NUM":
                raise CalculationError("Missing operator between numbers")
            raise CalculationError(f"Unexpected '{text}'")
        return value

    def _expr(self) -> Decimal:
        self._enter()
        value = self._term()
        while self._is_op("+", "-"):
            op = self._next()[1]
            right = self._term()
            value = value + right if op == "+" else value - right
        self._leave()
        return value

    def _term(self) -> Decimal:
        value = self._unary()
        while True:
            if self._is_op("*", "/", "%"):
                op = self._next()[1]
                right = self._unary()
                value = self._binary(op, value, right)
            elif self._starts_implicit_factor():
                value = value * self._unary()        # 2pi, 3(4+5), 2sin(30)
            else:
                return value

    def _starts_implicit_factor(self) -> bool:
        kind, text = self._peek()
        return kind == "NAME" or (kind == "OP" and text == "(")

    def _binary(self, op: str, left: Decimal, right: Decimal) -> Decimal:
        if op == "*":
            return left * right
        if right == 0:
            raise CalculationError("Cannot divide by zero")
        if op == "/":
            return left / right
        return left % right  # '%': remainder, sign follows the left operand

    def _unary(self) -> Decimal:
        if self._is_op("+", "-"):
            self._enter()
            op = self._next()[1]
            value = self._unary()
            self._leave()
            return -value if op == "-" else value
        return self._power()

    def _power(self) -> Decimal:
        base = self._postfix()
        if self._is_op("^"):
            self._require_scientific("^")
            self._next()
            exponent = self._signed_power()
            return self._pow(base, exponent)
        return base

    def _signed_power(self) -> Decimal:
        """Right-hand side of '^': allows a sign (2^-3) and chains (2^3^2)."""
        if self._is_op("+", "-"):
            self._enter()
            op = self._next()[1]
            value = self._signed_power()
            self._leave()
            return -value if op == "-" else value
        return self._power()

    def _postfix(self) -> Decimal:
        value = self._primary()
        while self._is_op("!"):
            self._require_scientific("!")
            self._next()
            value = self._factorial(value)
        return value

    def _primary(self) -> Decimal:
        kind, text = self._next()

        if kind == "NUM":
            return Decimal(text)

        if kind == "NAME":
            self._require_scientific(text)
            if text in FUNCTIONS:
                if not self._is_op("("):
                    raise CalculationError(f"'{text}' must be followed by '('")
                self._next()
                argument = self._expr()
                self._expect_close()
                return self._apply_function(text, argument)
            if text in CONSTANTS:
                return _E if text == "e" else _PI
            raise CalculationError(f"Unknown name '{text}'")

        if kind == "OP" and text == "(":
            value = self._expr()
            self._expect_close()
            return value

        if kind == "END":
            raise CalculationError("Expression ended unexpectedly")
        raise CalculationError(f"Unexpected '{text}'")

    def _expect_close(self) -> None:
        if not self._is_op(")"):
            raise CalculationError("Mismatched parentheses: missing ')'")
        self._next()

    def _require_scientific(self, what: str) -> None:
        if not self.scientific:
            raise CalculationError(
                f"'{what}' is not available in the basic calculator - use the Scientific tab"
            )

    # -- operations --------------------------------------------------------- #
    def _pow(self, base: Decimal, exponent: Decimal) -> Decimal:
        if base == 0:
            if exponent < 0:
                raise CalculationError("Cannot divide by zero")
            return Decimal(1) if exponent == 0 else Decimal(0)
        if base < 0 and not _is_integral(exponent):
            raise CalculationError("Cannot raise a negative number to a fractional power")
        _check_power_size(base, exponent)
        result = base ** exponent
        return result if _is_integral(exponent) else _clean_inexact(result)

    def _factorial(self, value: Decimal) -> Decimal:
        if value < 0 or not _is_integral(value):
            raise CalculationError("Factorial needs a whole number that is 0 or more")
        if value > MAX_FACTORIAL:
            raise CalculationError(f"Factorial is limited to {MAX_FACTORIAL}!")
        return Decimal(math.factorial(int(value)))

    def _apply_function(self, name: str, x: Decimal) -> Decimal:
        if name == "abs":
            return abs(x)
        if name == "sqrt":
            if x < 0:
                raise CalculationError("Cannot take the square root of a negative number")
            return x.sqrt()
        if name == "cbrt":
            if x == 0:
                return Decimal(0)
            root = _clean_inexact(abs(x) ** (Decimal(1) / Decimal(3)))
            return -root if x < 0 else root
        if name == "ln":
            if x <= 0:
                raise CalculationError("ln is only defined for numbers greater than 0")
            return _clean_inexact(x.ln())
        if name == "log":
            if x <= 0:
                raise CalculationError("log is only defined for numbers greater than 0")
            result = x.log10()
            return result if _is_integral(result) else _clean_inexact(result)
        if name == "exp":
            if x > 2000:
                raise CalculationError("Result is too large to calculate")
            return _clean_inexact(x.exp())
        if name in ("sin", "cos", "tan"):
            return self._trig(name, x)
        if name in ("asin", "acos", "atan"):
            return self._inverse_trig(name, x)
        raise CalculationError(f"Unknown function '{name}'")  # pragma: no cover

    def _trig(self, name: str, x: Decimal) -> Decimal:
        if abs(x) > Decimal("1e15"):
            raise CalculationError("Angle is too large")

        if self.degrees:
            angle = x % 360                       # exact, keeps sign of x
            if angle < 0:
                angle += 360
            half = angle % 180                    # 0..180
            # exact answers for the multiples of 90 degrees
            if name == "sin":
                if half == 0:
                    return Decimal(0)
                if angle == 90:
                    return Decimal(1)
                if angle == 270:
                    return Decimal(-1)
            elif name == "cos":
                if half == 90:
                    return Decimal(0)
                if angle == 0:
                    return Decimal(1)
                if angle == 180:
                    return Decimal(-1)
            else:  # tan
                if half == 0:
                    return Decimal(0)
                if half == 90:
                    raise CalculationError("tan is undefined at this angle")
            radians = angle * _PI / 180
        else:
            radians = x

        sin_value, cos_value = _sin_cos(radians)
        if name == "tan":
            if abs(cos_value) < _ZERO_NOISE:
                raise CalculationError("tan is undefined at this angle")
            value = sin_value / cos_value
        else:
            value = sin_value if name == "sin" else cos_value

        # sin(pi) is 0, not 1e-63: remove series/pi rounding noise (radian mode only matters here)
        if abs(value) < _ZERO_NOISE and abs(radians) >= Decimal("0.001"):
            return Decimal(0)
        return _clean_inexact(value)

    def _inverse_trig(self, name: str, x: Decimal) -> Decimal:
        if name in ("asin", "acos") and abs(x) > 1:
            raise CalculationError(f"{name} is only defined for values from -1 to 1")

        if name == "atan":
            radians = _atan(x)
        else:
            if abs(x) == 1:
                asin_value = _HALF_PI if x > 0 else -_HALF_PI
            else:
                asin_value = _atan(x / (1 - x * x).sqrt())
            radians = asin_value if name == "asin" else _HALF_PI - asin_value

        result = radians * 180 / _PI if self.degrees else radians
        return _clean_inexact(result)


# --------------------------------------------------------------------------- #
# Output formatting
# --------------------------------------------------------------------------- #
def format_result(value: Decimal) -> str:
    """
    Turn a Decimal into the string shown to the user.

    * whole numbers (up to 30 digits) are printed exactly
    * everything else is rounded to 15 significant digits, trailing zeros removed
    * very large / very small numbers use scientific notation (1.5e+30)
    """
    if value.is_nan() or value.is_infinite():
        raise CalculationError("Result is not a finite number")
    if value == 0:
        return "0"

    if _is_integral(value) and value.adjusted() < MAX_EXACT_INTEGER_DIGITS:
        return str(int(value))

    display_ctx = Context(prec=DISPLAY_DIGITS, rounding=ROUND_HALF_EVEN)
    try:
        rounded = display_ctx.plus(value)
    except (InvalidOperation, Overflow):
        raise CalculationError("Result is too large to display")
    exponent = rounded.adjusted()

    if -7 <= exponent < 21:
        text = format(rounded, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return "0" if text in ("", "-0") else text

    text = format(display_ctx.normalize(rounded), "E")
    return text.replace("E", "e")


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def evaluate_decimal(expression: str, *, scientific: bool = False, degrees: bool = True) -> Decimal:
    """Evaluate ``expression`` and return the unrounded Decimal result."""
    if not isinstance(expression, str) or not expression.strip():
        raise CalculationError("Expression is empty")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise CalculationError(f"Expression is too long (max {MAX_EXPRESSION_LENGTH} characters)")

    tokens = _tokenize(expression)
    context = Context(
        prec=WORKING_PRECISION,
        rounding=ROUND_HALF_EVEN,
        Emin=-999999,
        Emax=999999,
        traps=[InvalidOperation, DivisionByZero, Overflow],
    )
    try:
        with localcontext(context):
            return _Parser(tokens, scientific=scientific, degrees=degrees).parse()
    except CalculationError:
        raise
    except DivisionByZero:
        raise CalculationError("Cannot divide by zero")
    except (InvalidOperation, Overflow):
        raise CalculationError("Result is undefined or too large to calculate")
    except RecursionError:
        raise CalculationError("Expression is nested too deeply")


def evaluate(expression: str, *, scientific: bool = False, degrees: bool = True) -> str:
    """Evaluate ``expression`` and return the formatted answer as a string."""
    return format_result(evaluate_decimal(expression, scientific=scientific, degrees=degrees))
