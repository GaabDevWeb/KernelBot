from fastapi.testclient import TestClient

from app.factory import create_app


def test_chat_rejects_request_without_message() -> None:
    response = TestClient(create_app()).post("/chat", json={"channel": "cli"})

    assert response.status_code == 422
    assert "message" in response.text
