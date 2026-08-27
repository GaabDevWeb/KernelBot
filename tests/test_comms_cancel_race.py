"""Race cancelamento × execução de campanhas (comms scheduler)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from kernel.comms.service import execute_campaign
from kernel.comms.store import CommsStore


@pytest.fixture
def store(tmp_path: Path) -> CommsStore:
    return CommsStore(tmp_path / "comms_race.sqlite3")


def _campaign(store: CommsStore, *, status: str = "scheduled") -> str:
    return store.create_campaign(
        title="Race test",
        body="Olá turma",
        channel="whatsapp",
        dest_type="user",
        dest_ref="5511999@s.whatsapp.net",
        status=status,
    )


def test_cancelled_campaign_never_sends(store: CommsStore) -> None:
    cid = _campaign(store, status="cancelled")

    async def _run():
        with patch("kernel.comms.service.get_comms_store", return_value=store):
            with patch("kernel.comms.service._send_one", new_callable=AsyncMock) as send_mock:
                result = await execute_campaign(cid)
        assert result["error"] == "cancelled"
        send_mock.assert_not_called()

    asyncio.run(_run())


def test_cancel_during_send_aborts_remaining(store: CommsStore) -> None:
    cid = _campaign(store)
    calls = {"n": 0}

    async def _slow_send(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            store.update_campaign_status(cid, "cancelled")
        return {"ok": True, "latency_ms": 1}

    async def _run():
        with patch("kernel.comms.service.get_comms_store", return_value=store):
            with patch("kernel.comms.service.expand_destinations") as expand:
                expand.return_value = [
                    ("user", "5511111@s.whatsapp.net"),
                    ("user", "5522222@s.whatsapp.net"),
                ]
                with patch("kernel.comms.service._send_one", side_effect=_slow_send):
                    return await execute_campaign(cid)

    result = asyncio.run(_run())
    assert result.get("error") == "cancelled"
    assert calls["n"] == 1


def test_concurrent_claim_only_one_sends(store: CommsStore) -> None:
    cid = _campaign(store)
    send_count = {"n": 0}

    async def _send(**kwargs):
        send_count["n"] += 1
        await asyncio.sleep(0.05)
        return {"ok": True, "latency_ms": 1}

    async def _run():
        with patch("kernel.comms.service.get_comms_store", return_value=store):
            with patch("kernel.comms.service._send_one", side_effect=_send):
                return await asyncio.gather(
                    execute_campaign(cid),
                    execute_campaign(cid),
                )

    results = asyncio.run(_run())
    successes = [r for r in results if r.get("sent", 0) > 0]
    failures = [r for r in results if r.get("error") == "not_claimable"]
    assert len(successes) == 1
    assert len(failures) == 1
    assert send_count["n"] >= 1
