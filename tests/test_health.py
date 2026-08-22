from fastapi.testclient import TestClient

from app.factory import create_app


def test_health_is_available_without_infrastructure() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
