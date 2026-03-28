from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "orchestrator"


def test_ready_without_redis():
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json().get("ready") is True
