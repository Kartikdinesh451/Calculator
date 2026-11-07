"""
Smoke test for a RUNNING server:   python test_api.py   (start it first: cd backend && uvicorn main:app)
Uses only the standard library. For the full automated suite run:  cd backend && pytest
"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api"


def post(path, body):
    request = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


CASES = [
    ("/calculator/calculate", {"expression": "3 + 5"}, 200, "result", "8"),
    ("/calculator/calculate", {"expression": "2 + 3 * 4"}, 200, "result", "14"),
    ("/calculator/calculate", {"expression": "0.1 + 0.2"}, 200, "result", "0.3"),
    ("/calculator/calculate", {"expression": "1 / 0"}, 400, "detail", "Cannot divide by zero"),
    ("/scientific/calculate", {"expression": "sin(30)", "is_degree": True}, 200, "result", "0.5"),
    ("/scientific/calculate", {"expression": "abs(-5)"}, 200, "result", "5"),
    ("/scientific/calculate", {"expression": "2π"}, 200, "result", "6.28318530717959"),
    ("/financial/loan", {"principal": 10000, "rate": 5, "term": 36}, 200, "emi", 299.71),
    ("/financial/interest", {"principal": 10000, "rate": 5, "time": 5, "type": "compound"}, 200, "total_amount", 12762.82),
    ("/financial/mortgage", {"price": 300000, "down_payment": 60000, "rate": 4.5, "term": 30}, 200, "monthly_payment", 1216.04),
    ("/financial/roi", {"initial_investment": 10000, "final_value": 15000}, 200, "roi_percentage", 50.0),
]

failed = 0
for path, body, want_status, key, want in CASES:
    try:
        status, data = post(path, body)
    except urllib.error.URLError as error:
        sys.exit(f"Cannot reach the server ({error.reason}). Start it first: cd backend && uvicorn main:app")
    ok = status == want_status and data.get(key) == want
    failed += not ok
    print(("PASS" if ok else "FAIL"), path, body, "->", status, data.get(key))

print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
sys.exit(1 if failed else 0)
