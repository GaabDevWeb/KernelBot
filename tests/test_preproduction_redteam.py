"""Testes reprodutíveis do PRE-PRODUCTION RED TEAM (Kernel).

Cada teste mapeia a um finding REDTEAM-xxx em docs/security/preproduction-redteam.md.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.rate_limit import reset_for_tests
from app.factory import create_app
from app.state import AppServices
from kernel.memory.group_memory import GroupMemoryStore
from kernel.memory.idempotency import IdempotencyStore
from kernel.memory.pinned_store import PinnedSessionStore
from kernel.memory.transcript_store import TranscriptStore
from kernel.orchestrator.context import BuildMessagesResult, ContextTrace


@pytest.fixture(autouse=True)
def _isolated_rate_limit():
    reset_for_tests()
    yield
    reset_for_tests()


class ChatProviderStub:
    async def stream_response(self, *_args, **_kwargs):
        yield 'data: [ACL_META]{"confidence":"high","sources":[],"label":"Python"}\n\n'
        yield "data: Resposta simulada\n\n"
        yield "data: [DONE]\n\n"


class ContextManagerStub:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(
            transcript_max_turns=16,
            group_memory_enabled=True,
            group_profile_enabled=True,
            group_profile_update_threshold=50,
        )

    def build_messages(self, message, **kwargs):
        trace = ContextTrace(label="Python", sources=(), source_details=())
        return BuildMessagesResult(
            messages=[{"role": "user", "content": message}],
            trace=trace,
            effective_discipline="python",
        )


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    mem_store = GroupMemoryStore(tmp_path / "redteam_group.sqlite3")
    services = AppServices(
        search_engine=SimpleNamespace(),  # type: ignore[arg-type]
        context_manager=ContextManagerStub(),  # type: ignore[arg-type]
        chat_provider=ChatProviderStub(),  # type: ignore[arg-type]
        pinned_store=PinnedSessionStore(),
        transcript_store=TranscriptStore(),
        group_memory_store=mem_store,
        idempotency_store=IdempotencyStore(default_ttl_seconds=60),
    )
    return TestClient(create_app(services))


def test_redteam_001_dev_mode_allows_unauthenticated_v1_chat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REDTEAM-001: sem ACL_REQUIRE_API_AUTH e fora de production, /v1/chat é público."""
    monkeypatch.delenv("ACL_REQUIRE_API_AUTH", raising=False)
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    client = _client(tmp_path, monkeypatch)

    r = client.post(
        "/v1/chat",
        json={
            "context": {
                "platform": "whatsapp",
                "user_id": "attacker",
                "channel_id": "any@g.us",
            },
            "message": "ping sem bearer",
        },
    )
    assert r.status_code == 200


def test_redteam_002_global_bearer_cross_group_idor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REDTEAM-002: um Bearer global lê/apaga memória de qualquer channel_id."""
    monkeypatch.setenv("ACL_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("ACL_API_BEARER_TOKEN", "global-secret")
    client = _client(tmp_path, monkeypatch)
    headers = {"Authorization": "Bearer global-secret"}

    victim = "victim-secret-group@g.us"
    ingest = client.post(
        "/v1/groups/messages",
        json={
            "platform": "whatsapp",
            "channel_id": victim,
            "messages": [
                {
                    "message_id": "sec-1",
                    "user_id": "alice",
                    "content": "Segredo do grupo vítima: ALPHA-999",
                }
            ],
        },
        headers=headers,
    )
    assert ingest.status_code == 200

    hist = client.get(
        f"/v1/groups/whatsapp/{victim}/history?query=ALPHA",
        headers=headers,
    )
    assert hist.status_code == 200
    assert hist.json()["count"] >= 1

    other_channel = "attacker-other-group@g.us"
    wipe = client.delete(
        f"/v1/groups/whatsapp/{victim}/memory",
        headers=headers,
    )
    assert wipe.status_code == 200
    assert client.get(
        f"/v1/groups/whatsapp/{victim}/history?query=ALPHA",
        headers=headers,
    ).json()["count"] == 0

    # Mesmo token, outro grupo — sem restrição adicional
    assert client.get(
        f"/v1/groups/whatsapp/{other_channel}/state",
        headers=headers,
    ).status_code == 200


def test_redteam_008_group_memory_storage_isolation(tmp_path: Path) -> None:
    """REDTEAM-008 (PASS): BM25/SQLite não vazam entre channel_id."""
    store = GroupMemoryStore(tmp_path / "iso.sqlite3")
    store.record_message(
        platform="whatsapp",
        channel_id="group-A@g.us",
        message_id="a1",
        user_id="u1",
        content="TOKEN-SECRETO-GRUPO-A",
    )
    store.record_message(
        platform="whatsapp",
        channel_id="group-B@g.us",
        message_id="b1",
        user_id="u2",
        content="ola grupo B",
    )
    leaked = store.search_historical("whatsapp", "group-B@g.us", "TOKEN-SECRETO")
    assert leaked == []


def test_redteam_003_async_profile_update_logs_on_failure(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """REDTEAM-003: falha de profile em background não pode ser silenciosa."""
    import asyncio
    import logging

    from api.routes_v1 import _async_update_group_profile

    store = GroupMemoryStore(tmp_path / "prof.sqlite3")
    caplog.set_level(logging.WARNING, logger="kernelbots.api.v1")

    with patch(
        "api.routes_v1.GroupProfileAnalyzer.extract_profile",
        side_effect=RuntimeError("simulated profile failure"),
    ):
        asyncio.run(_async_update_group_profile(store, "whatsapp", "g@test"))

    assert any("profile" in rec.message.lower() or "simulated" in rec.message.lower()
               for rec in caplog.records)


def test_redteam_009_production_rejects_missing_api_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """REDTEAM-009 (PASS): fail-fast em production sem tokens configurados."""
    from api.security import validate_production_security_config

    monkeypatch.setenv("KERNELBOT_ENV", "production")
    monkeypatch.delenv("ACL_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("ACL_CHANNEL_API_KEYS", raising=False)
    monkeypatch.delenv("ACL_INTERNAL_BEARER_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="ACL_API_BEARER_TOKEN|ACL_CHANNEL_API_KEYS"):
        validate_production_security_config()


def test_redteam_001_staging_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """REDTEAM-001 remediated: staging exige auth mesmo sem ACL_REQUIRE_API_AUTH."""
    from api.security import require_api_auth

    monkeypatch.setenv("KERNELBOT_ENV", "staging")
    monkeypatch.delenv("ACL_REQUIRE_API_AUTH", raising=False)
    assert require_api_auth() is True
