from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health_and_test_engine():
    assert client.get("/health").json()["status"] == "ok"
    result = client.post("/api/v1/tests/communication")
    assert result.status_code == 200
    assert result.json()["passed"] is True


def test_invalid_register_is_client_error():
    assert client.get("/api/v1/registers/35").status_code == 400

