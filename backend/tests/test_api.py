"""HTTP-level tests. Skipped automatically if fastapi/httpx are not installed."""
import importlib

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CALCULATOR_DB", str(tmp_path / "api.db"))
    from app.models import database
    importlib.reload(database)
    import app.routers.calculator, app.routers.scientific, app.routers.financial, app.routers.history
    for module in (app.routers.calculator, app.routers.scientific, app.routers.financial, app.routers.history):
        importlib.reload(module)
    import main
    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c


def test_basic(client):
    r = client.post("/api/calculator/calculate", json={"expression": "3 + 5"})
    assert r.status_code == 200 and r.json() == {"result": "8", "expression": "3 + 5"}
    assert client.post("/api/calculator/calculate", json={"expression": "1/0"}).status_code == 400
    assert client.post("/api/calculator/calculate", json={"expression": ""}).status_code == 422


def test_scientific(client):
    r = client.post("/api/scientific/calculate", json={"expression": "sin(30)", "is_degree": True})
    assert r.json()["result"] == "0.5"
    r = client.post("/api/scientific/calculate", json={"expression": "abs(-5)"})
    assert r.json()["result"] == "5"


def test_financial(client):
    r = client.post("/api/financial/loan", json={"principal": 10000, "rate": 5, "term": 36})
    assert r.json()["emi"] == 299.71
    r = client.post("/api/financial/interest", json={"principal": 10000, "rate": 5, "time": 5, "type": "compound"})
    assert r.json()["total_amount"] == 12762.82
    r = client.post("/api/financial/mortgage", json={"price": 300000, "down_payment": 60000, "rate": 4.5, "term": 30})
    assert r.json()["monthly_payment"] == 1216.04
    r = client.post("/api/financial/roi", json={"initial_investment": 10000, "final_value": 15000})
    assert r.json()["roi_percentage"] == 50.0
    assert client.post("/api/financial/mortgage",
                       json={"price": 100, "down_payment": 100, "rate": 5, "term": 10}).status_code == 400
    assert client.post("/api/financial/loan", json={"principal": 1000, "rate": 0, "term": 12}).status_code == 200


def test_history(client):
    client.post("/api/calculator/calculate", json={"expression": "2+2"})
    client.post("/api/calculator/calculate", json={"expression": "1/0"})       # failed calc is not stored
    items = client.get("/api/history/").json()["history"]
    assert len(items) == 1 and items[0]["result"] == "4"
    assert client.delete("/api/history/").status_code == 200
    assert client.get("/api/history/").json()["history"] == []


def test_frontend_is_served(client):
    assert "All-in-One Calculator" in client.get("/").text
    assert client.get("/health").json() == {"status": "healthy"}
