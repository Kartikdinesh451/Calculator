import pytest

from app.services.calculator_service import calculate_basic
from app.services.expression_engine import CalculationError, evaluate
from app.services.scientific_service import calculate_scientific


# ---------------------------------------------------------------- basic maths
@pytest.mark.parametrize("expr, expected", [
    ("3 + 5", "8"),
    ("2+3*4", "14"),                      # precedence
    ("(2+3)*4", "20"),
    ("10-4-3", "3"),                      # left associative
    ("100/8/5", "2.5"),
    ("0.1+0.2", "0.3"),                   # float gives 0.30000000000000004
    ("0.00001*2", "0.00002"),             # old code rounded to 4 places -> 0
    ("1/3", "0.333333333333333"),
    ("2/3", "0.666666666666667"),
    ("1/3*3", "1"),
    ("07+1", "8"),                        # old code: SyntaxError
    ("12345678901234567890+1", "12345678901234567891"),   # exact big int
    ("99999999999*99999999999", "9999999999800000000001"),
    ("-5+3", "-2"),
    ("5*-3", "-15"),
    ("--5", "5"),
    ("+5", "5"),
    ("17%5", "2"),
    ("-7%3", "-1"),
    ("7.5%2", "1.5"),
    (".5+.5", "1"),
    ("5.", "5"),
    ("  12  *  3 ", "36"),
    ("6×7", "42"),
    ("84÷4", "21"),
    ("9−4", "5"),
    ("1e3+1", "1001"),
    ("0", "0"),
    ("-0", "0"),
    ("0.1*3", "0.3"),
    ("1-0.9", "0.1"),
    ("123456789.123456789*1", "123456789.123457"),
])
def test_basic_ok(expr, expected):
    assert calculate_basic(expr) == expected


@pytest.mark.parametrize("expr, message", [
    ("1/0", "divide by zero"),
    ("5%0", "divide by zero"),
    ("(1+2", "missing ')'"),
    ("1+2)", "extra ')'"),
    ("2 3", "Missing operator"),
    ("1.2.3", "Missing operator"),
    ("5+", "ended unexpectedly"),
    ("*5", "Unexpected"),
    ("", "empty"),
    ("   ", "empty"),
    ("()", "Unexpected"),
    ("2**3", "not available in the basic"),
    ("sin(1)", "not available in the basic"),
    ("5!", "not available in the basic"),
    ("__import__('os').system('id')", "Unexpected character"),
    ("open('/etc/passwd')", "Unexpected character"),
    ("1;2", "Unexpected character"),
    ("2" + "+2" * 400, "too long"),
])
def test_basic_errors(expr, message):
    with pytest.raises(CalculationError) as err:
        calculate_basic(expr)
    assert message.lower() in str(err.value).lower()


def test_deep_nesting_is_rejected_not_crashing():
    with pytest.raises(CalculationError):
        calculate_basic("(" * 200 + "1" + ")" * 200)
    with pytest.raises(CalculationError):
        calculate_basic("-" * 400 + "1")


# ------------------------------------------------------------- scientific maths
def sci(expr, degrees=True):
    return calculate_scientific(expr, degrees)


@pytest.mark.parametrize("expr, expected", [
    ("sin(30)", "0.5"),                   # old code: SyntaxError (unbalanced parenthesis)
    ("sin(0)", "0"),
    ("sin(90)", "1"),
    ("sin(180)", "0"),
    ("sin(270)", "-1"),
    ("sin(-30)", "-0.5"),
    ("sin(390)", "0.5"),
    ("cos(60)", "0.5"),
    ("cos(90)", "0"),
    ("cos(180)", "-1"),
    ("cos(0)", "1"),
    ("tan(45)", "1"),
    ("tan(0)", "0"),
    ("tan(135)", "-1"),
    ("sin(45)", "0.707106781186548"),
    ("asin(0.5)", "30"),
    ("acos(0.5)", "60"),
    ("atan(1)", "45"),
    ("asin(1)", "90"),
    ("abs(-5)", "5"),                     # old code: math.abs does not exist
    ("abs(3-10)", "7"),
    ("sqrt(16)", "4"),
    ("sqrt(2)", "1.4142135623731"),
    ("sqrt(0.25)", "0.5"),
    ("cbrt(27)", "3"),
    ("cbrt(-8)", "-2"),
    ("cbrt(27)-3", "0"),
    ("log(1000)", "3"),
    ("log(0.001)", "-3"),
    ("log(2)", "0.301029995663981"),
    ("ln(e)", "1"),
    ("ln(1)", "0"),
    ("ln(10)", "2.30258509299405"),
    ("exp(0)", "1"),
    ("exp(1)", "2.71828182845905"),
    ("pi", "3.14159265358979"),
    ("π", "3.14159265358979"),
    ("e", "2.71828182845905"),
    ("2π", "6.28318530717959"),           # old code: "23.1416"
    ("2*π", "6.28318530717959"),
    ("π*2^2", "12.5663706143592"),
    ("2^3", "8"),
    ("2^10", "1024"),
    ("2^0.5", "1.4142135623731"),
    ("2^-2", "0.25"),
    ("2^3^2", "512"),                     # right associative
    ("-2^2", "-4"),
    ("(-2)^2", "4"),
    ("(-2)^3", "-8"),
    ("0^0", "1"),
    ("0^5", "0"),
    ("10^25", "10000000000000000000000000"),
    ("2^100", "1.26765060022823e+30"),
    ("2**3", "8"),
    ("5!", "120"),
    ("0!", "1"),
    ("3!^2", "36"),
    ("2^3!", "64"),
    ("20!", "2432902008176640000"),
    ("100!", "9.33262154439442e+157"),
    ("3(4+5)", "27"),
    ("2sin(30)", "1"),
    ("(1+2)(3+4)", "21"),
    ("sin(30)^2+cos(30)^2", "1"),
    ("sqrt(9)+sqrt(16)", "7"),
    ("√(81)", "9"),
    ("SIN(30)", "0.5"),
    ("sin(30+60)", "1"),
    ("2*sin(30)*cos(60)", "0.5"),
    ("1e-10*1", "1e-10"),
    ("1/3+1/3+1/3", "1"),
])
def test_scientific_degrees(expr, expected):
    assert sci(expr) == expected


@pytest.mark.parametrize("expr, expected", [
    ("sin(pi)", "0"),
    ("sin(pi/2)", "1"),
    ("sin(pi/6)", "0.5"),
    ("cos(pi)", "-1"),
    ("cos(pi/2)", "0"),
    ("cos(pi/3)", "0.5"),
    ("tan(pi/4)", "1"),
    ("sin(2pi)", "0"),
    ("sin(1)", "0.841470984807897"),
    ("cos(1)", "0.54030230586814"),
    ("atan(1)", "0.785398163397448"),
    ("asin(1)", "1.5707963267949"),
])
def test_scientific_radians(expr, expected):
    assert sci(expr, degrees=False) == expected


@pytest.mark.parametrize("expr, message", [
    ("tan(90)", "undefined"),
    ("tan(270)", "undefined"),
    ("sqrt(-1)", "negative"),
    ("ln(0)", "greater than 0"),
    ("ln(-5)", "greater than 0"),
    ("log(0)", "greater than 0"),
    ("asin(2)", "-1 to 1"),
    ("acos(-1.5)", "-1 to 1"),
    ("(-8)^(1/3)", "negative number"),
    ("0^-1", "divide by zero"),
    ("(-1)!", "whole number"),
    ("2.5!", "whole number"),
    ("5000!", "limited"),
    ("9^9^9^9", "too large"),
    ("10^100000", "too large"),
    ("exp(100000)", "too large"),
    ("sin", "must be followed"),
    ("foo(2)", "Unknown name"),
    ("xyz", "Unknown name"),
    ("sin(1,2)", "missing ')'"),
    ("sin()", "Unexpected"),
    ("sin(1e20)", "too large"),
    ("__import__('os')", "Unexpected character"),
    ("().__class__", "Unexpected"),
])
def test_scientific_errors(expr, message):
    with pytest.raises(CalculationError) as err:
        sci(expr)
    assert message.lower() in str(err.value).lower()


def test_tan_undefined_in_radians():
    with pytest.raises(CalculationError):
        sci("tan(pi/2)", degrees=False)


def test_huge_power_is_fast():
    import time
    start = time.time()
    for expr in ("9^9^9^9", "2^2^2^2^2^2", "99999999^99999999"):
        with pytest.raises(CalculationError):
            sci(expr)
    assert time.time() - start < 2


def test_degree_and_radian_differ():
    assert sci("sin(30)", True) == "0.5"
    assert sci("sin(30)", False) == "-0.988031624092862"


def test_no_python_code_is_ever_executed():
    for evil in ["__import__('os').system('echo hi')", "exec('1')", "eval('1')", "[].__class__",
                 "lambda: 1", "open('x')", "'a'*5", "1 if 1 else 2"]:
        with pytest.raises(CalculationError):
            sci(evil)


def test_evaluate_returns_string():
    assert isinstance(evaluate("1+1"), str)
