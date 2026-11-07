import importlib


def test_history_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("CALCULATOR_DB", str(tmp_path / "t.db"))
    from app.models import database
    database = importlib.reload(database)

    database.init_db()
    assert database.get_history() == []
    database.add_history("1+1", "2", "basic")
    database.add_history("sin(30)  [deg]", "0.5", "scientific")
    items = database.get_history()
    assert [i["result"] for i in items] == ["0.5", "2"]          # newest first
    assert items[0]["calculator_type"] == "scientific"
    assert items[0]["timestamp"].endswith("+00:00")
    assert len(database.get_history(limit=1)) == 1
    database.clear_history()
    assert database.get_history() == []


def test_database_path_independent_of_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("CALCULATOR_DB", raising=False)
    monkeypatch.chdir(tmp_path)
    from app.models import database
    database = importlib.reload(database)
    assert database.DB_PATH.is_absolute()
    assert database.DB_PATH.name == "calculator.db"
    assert database.DB_PATH.parent.name == "backend"


def test_reads_rows_written_by_old_version(tmp_path, monkeypatch):
    import sqlite3
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE calculation_history (id INTEGER PRIMARY KEY, expression VARCHAR NOT NULL, "
                 "result VARCHAR NOT NULL, timestamp DATETIME, calculator_type VARCHAR NOT NULL)")
    conn.execute("INSERT INTO calculation_history VALUES (1,'3 + 5','8.0','2026-10-12 10:00:00.123456','basic')")
    conn.commit(); conn.close()
    monkeypatch.setenv("CALCULATOR_DB", str(path))
    from app.models import database
    database = importlib.reload(database)
    database.init_db()
    item = database.get_history()[0]
    assert item["timestamp"].startswith("2026-10-12T10:00:00") and item["timestamp"].endswith("+00:00")
