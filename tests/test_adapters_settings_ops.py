"""Testes Ops P4 — Adapters + Configurações."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.factory import create_app
from kernel.comms.store import reset_comms_store_for_tests
from kernel.trace import reset_trace_bus_for_tests
from kernel.users.store import reset_users_store_for_tests


def _client(tmp_path: Path, monkeypatch, token: str = "p4-ops-token") -> TestClient:
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", token)
    monkeypatch.setenv("ACL_TRACE_DB_PATH", str(tmp_path / "traces.sqlite3"))
    monkeypatch.setenv("ACL_COMM_DB_PATH", str(tmp_path / "comms.sqlite3"))
    monkeypatch.setenv("ACL_USERS_DB_PATH", str(tmp_path / "users.sqlite3"))
    monkeypatch.setenv("KERNEL_VERSION", "test-p4")
    monkeypatch.setenv("ACL_LLM_PROVIDER", "cursor")
    monkeypatch.setenv("ACL_CURSOR_MODEL", "composer-2.5")
    monkeypatch.setenv("ORBIT_INTERNAL_URL", "http://127.0.0.1:8010")
    monkeypatch.delenv("ENV", raising=False)
    reset_trace_bus_for_tests()
    reset_comms_store_for_tests()
    reset_users_store_for_tests()
    return TestClient(create_app())


def test_adapters_and_settings_require_auth(tmp_path: Path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        for path in (
            "/ops/adapters/whatsapp",
            "/ops/adapters/discord",
            "/ops/settings/models",
            "/ops/settings/prompts",
            "/ops/settings/providers",
            "/ops/settings/system",
        ):
            r = client.get(path, follow_redirects=False)
            assert r.status_code == 303, path
            assert "/ops/login" in r.headers.get("location", "")
    reset_trace_bus_for_tests()
    reset_comms_store_for_tests()
    reset_users_store_for_tests()


def test_adapters_whatsapp_and_discord_pages(tmp_path: Path, monkeypatch):
    fake_status = {
        "ok": True,
        "ready": True,
        "reconnections": 2,
        "session": "wa-session-1",
        "token": "SHOULD_NOT_APPEAR",
        "api_key": "sk-secret-value",
    }
    with patch(
        "api.adapters_routes.whatsapp_status",
        new=AsyncMock(return_value=fake_status),
    ):
        with _client(tmp_path, monkeypatch) as client:
            client.post("/ops/login", data={"token": "p4-ops-token"}, follow_redirects=False)

            wa = client.get("/ops/adapters/whatsapp")
            assert wa.status_code == 200
            body = wa.content
            assert b"WhatsApp" in body
            assert b"ready" in body
            assert b"SHOULD_NOT_APPEAR" not in body
            assert b"sk-secret-value" not in body
            assert b"***" in body
            assert b"phase-pill" not in body or b">P4<" not in body

            disc = client.get("/ops/adapters/discord")
            assert disc.status_code == 200
            assert b"Discord" in disc.content
            assert b"discord_not_configured" in disc.content
            assert b"stub" in disc.content.lower()

    reset_trace_bus_for_tests()
    reset_comms_store_for_tests()
    reset_users_store_for_tests()


def test_settings_pages_readonly_and_redacted(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "cursor-test-key-do-not-leak")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    with _client(tmp_path, monkeypatch) as client:
        client.post("/ops/login", data={"token": "p4-ops-token"}, follow_redirects=False)

        models = client.get("/ops/settings/models")
        assert models.status_code == 200
        assert b"composer-2.5" in models.content
        assert b"0.7" in models.content
        assert b"Somente leitura" in models.content
        assert b"cursor-test-key-do-not-leak" not in models.content

        prompts = client.get("/ops/settings/prompts")
        assert prompts.status_code == 200
        assert b"system_prompt.txt" in prompts.content
        assert b"Somente leitura" in prompts.content

        prompts_file = client.get("/ops/settings/prompts?file=system_prompt.txt")
        assert prompts_file.status_code == 200
        assert b"Copiar" in prompts_file.content

        bad = client.get("/ops/settings/prompts?file=../../.env")
        assert bad.status_code == 200
        assert b"inv" in bad.content.lower() or b"Ficheiro" in bad.content

        providers = client.get("/ops/settings/providers")
        assert providers.status_code == 200
        assert b"cursor" in providers.content
        assert b"openrouter" in providers.content
        assert b"cursor-test-key-do-not-leak" not in providers.content

        system = client.get("/ops/settings/system")
        assert system.status_code == 200
        assert b"test-p4" in system.content
        assert b"configured" in system.content
        assert b"ACL_INTERNAL_BEARER_TOKEN" in system.content
        assert b"p4-ops-token" not in system.content
        assert b"cursor-test-key-do-not-leak" not in system.content

        # placeholders P4 removidos do menu
        dash = client.get("/ops/dashboard")
        assert dash.status_code == 200
        assert b'href="/ops/adapters/whatsapp"' in dash.content
        # phase pill P4 não deve aparecer junto a adapters/settings
        assert b">P4<" not in dash.content

    reset_trace_bus_for_tests()
    reset_comms_store_for_tests()
    reset_users_store_for_tests()


def test_prompt_path_traversal_blocked(tmp_path: Path, monkeypatch):
    from api.settings_routes import _safe_prompt_path

    assert _safe_prompt_path("system_prompt.txt") is not None
    assert _safe_prompt_path("../config.py") is None
    assert _safe_prompt_path("foo/bar.txt") is None
    assert _safe_prompt_path("") is None
