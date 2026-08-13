from fastapi.testclient import TestClient

from agent_arena.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["project"]


def test_runtime_health_shape():
    client = TestClient(app)
    resp = client.get("/health/runtime")
    assert resp.status_code == 200
    body = resp.json()
    assert "ok" in body
    assert "checks" in body
    checks = body["checks"]
    for key in (
        "appwrite_read",
        "appwrite_write",
        "event_persistence",
        "internal_key_configured",
        "modal_sandbox",
        "mock_mode",
        "universal_routing",
        "format_count",
    ):
        assert key in checks

