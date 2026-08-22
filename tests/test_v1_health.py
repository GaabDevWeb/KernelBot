"""Liveness de GET /v1/health — paridade com /health legado (sem infraestrutura)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.factory import create_app


def test_v1_health_is_available_without_services() -> None:
    response = TestClient(create_app()).get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_v1_health_is_available_with_none_services() -> None:
    response = TestClient(create_app(None)).get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
