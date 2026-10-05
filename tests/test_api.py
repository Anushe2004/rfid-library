from fastapi.testclient import TestClient

from rfidlib.api import app


def test_health_ok(env, monkeypatch):
    monkeypatch.setenv("RFIDLIB_DB", str(env["db"]))
    r = TestClient(app).get("/health")
    assert r.json() == {"status": "ok", "schema_version": 1}


def test_health_down_when_db_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("RFIDLIB_DB", str(tmp_path / "missing.db"))
    assert TestClient(app).get("/health").json()["status"] == "down"
    assert not (tmp_path / "missing.db").exists()


def test_version():
    assert TestClient(app).get("/version").json()["software_version"] == "0.1.0"
