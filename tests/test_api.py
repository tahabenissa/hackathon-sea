from fastapi.testclient import TestClient

from seashield.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_buoy_registry_lists_configured_buoys():
    ids = [b["buoy_id"] for b in client.get("/api/buoys").json()]
    assert ids == ["SS-B01", "SS-B02", "SS-B03", "SS-B04"]


def test_attack_scenarios_listed():
    assert "spike" in client.get("/api/attacks/scenarios").json()


def test_live_websocket_accepts_connections():
    with client.websocket_connect("/ws/live"):
        pass
