"""Testes Usuários Ops P2 — store, bloqueios, UI, export, 403 no chat."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from api.rate_limit import reset_for_tests
from app.factory import create_app
from kernel.comms.store import reset_comms_store_for_tests
from kernel.memory.session_key import v1_memory_key
from kernel.memory.transcript_store import TranscriptStore
from kernel.trace import reset_trace_bus_for_tests
from kernel.users.service import build_export_zip, is_user_blocked, touch_user_session
from kernel.users.store import (
    UsersStore,
    get_users_store,
    init_users_store,
    reset_users_store_for_tests,
)


def test_users_store_block_and_session(tmp_path: Path):
    store = UsersStore(tmp_path / "u.sqlite3")
    key = v1_memory_key("whatsapp", "5511999", "1:1")
    sid = store.touch_session(
        platform="whatsapp",
        user_id="5511999",
        channel_id="1:1",
        session_id=None,
        memory_key=key,
        increment_messages=1,
    )
    assert sid
    store.touch_session(
        platform="whatsapp",
        user_id="5511999",
        channel_id="1:1",
        session_id=None,
        memory_key=key,
        increment_messages=2,
    )
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].message_count == 3

    assert not store.is_blocked("whatsapp", "5511999")
    store.block_user(platform="whatsapp", user_id="5511999", reason="spam")
    assert store.is_blocked("whatsapp", "5511999")
    sessions = store.list_sessions()
    assert sessions[0].blocked
    assert store.unblock_user(platform="whatsapp", user_id="5511999")
    assert not store.is_blocked("whatsapp", "5511999")


def test_users_export_zip_contains_json_and_csv(tmp_path: Path):
    store = UsersStore(tmp_path / "export.sqlite3")
    key = v1_memory_key("whatsapp", "u-exp", "c1")
    store.touch_session(
        platform="whatsapp",
        user_id="u-exp",
        channel_id="c1",
        session_id=None,
        memory_key=key,
        increment_messages=2,
    )
    store.block_user(platform="whatsapp", user_id="u-exp", reason="export-test")
    data = build_export_zip(store)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = set(zf.namelist())
        assert "user_sessions.json" in names
        assert "user_sessions.csv" in names
        assert "user_blocks.json" in names
        assert "user_blocks.csv" in names
        assert "user_stats.json" in names
        assert "user_stats.csv" in names
        sessions = zf.read("user_sessions.json").decode()
        assert "u-exp" in sessions
        blocks = zf.read("user_blocks.json").decode()
        assert "export-test" in blocks


def test_transcript_list_keys():
    ts = TranscriptStore()
    ts.append_pair("k1", "oi", "ola", max_turns=4)
    assert "k1" in ts.list_keys()
    assert ts.list_summaries()[0]["pairs"] == 1


def test_users_ops_ui(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", "users-p2-token")
    monkeypatch.setenv("ACL_USERS_DB_PATH", str(tmp_path / "users.sqlite3"))
    monkeypatch.setenv("ACL_COMM_DB_PATH", str(tmp_path / "comms.sqlite3"))
    monkeypatch.setenv("ACL_TRACE_DB_PATH", str(tmp_path / "traces.sqlite3"))
    reset_trace_bus_for_tests()
    reset_comms_store_for_tests()
    reset_users_store_for_tests()

    app = create_app()
    with TestClient(app) as client:
        client.post("/ops/login", data={"token": "users-p2-token"}, follow_redirects=False)
        # seed session via store
        store = init_users_store(tmp_path / "users.sqlite3")
        key = v1_memory_key("whatsapp", "u1", "c1")
        sid = store.touch_session(
            platform="whatsapp",
            user_id="u1",
            channel_id="c1",
            session_id=None,
            memory_key=key,
            increment_messages=1,
        )
        for path in (
            "/ops/users/sessions",
            "/ops/users/conversations",
            "/ops/users/stats",
            "/ops/users/blocks",
        ):
            r = client.get(path)
            assert r.status_code == 200, path

        detail = client.get(f"/ops/users/conversations/{sid}")
        assert detail.status_code == 200
        assert b"u1" in detail.content

        export = client.get("/ops/users/export.zip")
        assert export.status_code == 200
        assert export.headers.get("content-type", "").startswith("application/zip")
        with zipfile.ZipFile(io.BytesIO(export.content)) as zf:
            assert "user_sessions.json" in zf.namelist()

        block = client.post(
            "/ops/users/blocks",
            data={"platform": "whatsapp", "user_id": "u1", "reason": "teste"},
            follow_redirects=False,
        )
        assert block.status_code == 303
        assert is_user_blocked("whatsapp", "u1")

    reset_users_store_for_tests()
    reset_comms_store_for_tests()
    reset_trace_bus_for_tests()


def test_v1_chat_blocked_user_returns_403(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ACL_USERS_DB_PATH", str(tmp_path / "users.sqlite3"))
    monkeypatch.setenv("ACL_COMM_DB_PATH", str(tmp_path / "comms.sqlite3"))
    monkeypatch.setenv("ACL_TRACE_DB_PATH", str(tmp_path / "traces.sqlite3"))
    monkeypatch.delenv("ACL_REQUIRE_API_AUTH", raising=False)
    reset_for_tests()
    reset_trace_bus_for_tests()
    reset_comms_store_for_tests()
    reset_users_store_for_tests()

    app = create_app()
    with TestClient(app) as client:
        store = get_users_store()
        assert store is not None
        store.block_user(platform="whatsapp", user_id="blocked-u", reason="spam")
        r = client.post(
            "/v1/chat",
            json={
                "context": {
                    "platform": "whatsapp",
                    "user_id": "blocked-u",
                    "channel_id": "c1",
                },
                "message": "oi",
            },
        )
        assert r.status_code == 403
        assert "bloqueado" in (r.json().get("detail") or "").lower()

    reset_users_store_for_tests()
    reset_comms_store_for_tests()
    reset_trace_bus_for_tests()
    reset_for_tests()


def test_touch_helper_noop_without_store():
    reset_users_store_for_tests()
    touch_user_session(
        platform="whatsapp",
        user_id="x",
        channel_id="y",
        session_id=None,
        memory_key="k",
        increment_messages=1,
    )
    assert not is_user_blocked("whatsapp", "x")
