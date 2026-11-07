# All-in-One Calculator (FastAPI + vanilla JS)

Basic, scientific and financial calculators. The browser sends an expression to a FastAPI
backend, which calculates it **exactly** (Python `Decimal`, no `eval`) and stores a history in SQLite.

## Run it

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows        (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
uvicorn main:app --reload
```

Open **http://localhost:8000** - the backend serves the frontend too, so there is nothing else to start.
(API docs: http://localhost:8000/docs)

You can still open `frontend/index.html` directly or serve it from another port; it then talks to
`http://localhost:8000/api` (CORS is enabled).

## Test it

```bash
cd backend
pip install -r requirements-dev.txt
pytest                      # ~175 tests: maths engine, financial formulas, history, HTTP API
cd .. && python test_api.py # optional smoke test against the running server
```

## Project structure

```
backend/
  main.py                          app, CORS, serves ../frontend
  app/models/schemas.py            request/response validation (pydantic)
  app/models/database.py           SQLite history (stdlib sqlite3)
  app/routers/                     calculator, scientific, financial, history endpoints
  app/services/expression_engine.py  safe parser + exact arithmetic  <- the core
  app/services/calculator_service.py / scientific_service.py / financial_service.py
  tests/
frontend/  index.html styles.css api.js calculator.js scientific.js financial.js history.js
```

## What the calculators accept

| Mode | Syntax |
|------|--------|
| Basic | `+ - * / %` (`%` = remainder, `17 % 5 = 2`), `( )`, decimals, `× ÷ −` |
| Scientific | everything above plus `^` (`2^3^2 = 512`, `-2^2 = -4`), `!`, `sin cos tan asin acos atan` (degrees or radians), `log` (base 10), `ln`, `sqrt`, `cbrt`, `abs`, `exp`, constants `pi`/`π`/`e`, implicit multiplication (`2π`, `3(4+5)`, `2sin(30)`) |

Answers are strings with up to 15 significant digits; whole numbers up to 30 digits are exact
(`12345678901234567890 + 1 = 12345678901234567891`). Very large/small numbers use `1.5e+30` form.

## API

| Method | Path | Body | Result |
|--------|------|------|--------|
| POST | `/api/calculator/calculate` | `{"expression": "2 + 3 * 4"}` | `{"result": "14", "expression": "..."}` |
| POST | `/api/scientific/calculate` | `{"expression": "sin(30)", "is_degree": true}` | `{"result": "0.5", ...}` |
| POST | `/api/financial/loan` | `{"principal": 10000, "rate": 5, "term": 36}` (months) | `emi`, `total_payment`, `total_interest` |
| POST | `/api/financial/interest` | `{"principal", "rate", "time", "type": "simple"\|"compound", "compounds_per_year": 1\|2\|4\|12\|365}` | `interest`, `total_amount` |
| POST | `/api/financial/mortgage` | `{"price", "down_payment", "rate", "term"}` (years) | `loan_amount`, `monthly_payment`, `total_payment`, `total_interest` |
| POST | `/api/financial/roi` | `{"initial_investment", "final_value"}` | `profit`, `roi_percentage` |
| GET / DELETE | `/api/history/` | - | history list / clear |

Invalid maths (e.g. `1/0`, `sqrt(-1)`) returns HTTP 400 `{"detail": "<readable message>"}`; invalid
field values return HTTP 422.

Financial results are rounded half-up to cents. `total_payment` is the exact EMI times the number of
months (not the rounded EMI times months), so it can differ from `emi * term` by a few cents.

## Configuration

* Database file: `backend/calculator.db` (override with the `CALCULATOR_DB` environment variable).
* Currency symbol: `CURRENCY_SYMBOL` at the top of `frontend/financial.js`.
* Backend URL for the frontend: `window.CALCULATOR_API_URL` or `API_BASE_URL` in `frontend/api.js`.
