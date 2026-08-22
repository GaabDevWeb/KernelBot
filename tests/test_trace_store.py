"""Testes do store SQLite TRACE + redacção."""

from __future__ import annotations

from pathlib import Path

from kernel.trace import redact_trace_data
from kernel.trace.store import TraceStore


def test_trace_store_mkdir_and_insert(tmp_path: Path):
    db = tmp_path / "nested" / "traces.sqlite3"
    store = TraceStore(db)
    assert db.parent.is_dir()
    store.insert_event(
        trace_id="t1",
        timestamp="2026-07-28T12:00:00.000Z",
        service="kernel",
        stage="REQUEST_RECEIVED",
        data={"ok": True},
        priority=10,
    )
    store.insert_event(
        trace_id="t1",
        timestamp="2026-07-28T12:00:01.000Z",
        service="orbit",
        stage="ERROR",
        data={"msg": "x"},
        priority=0,
    )
    summary = store.get_trace("t1")
    assert summary is not None
    assert summary.has_error
    assert "kernel" in summary.services and "orbit" in summary.services
    events = store.get_events("t1")
    assert len(events) == 2
    assert events[0].stage == "REQUEST_RECEIVED"
    assert events[1].stage == "ERROR"


def test_redact_trace_data_strips_tokens():
    out = redact_trace_data(
        {
            "Authorization": "Bearer secret-token",
            "api_key": "sk-abc",
            "nested": {"password": "pw", "ok": "yes"},
            "message": "hello",
        }
    )
    assert out["Authorization"] == "***"
    assert out["api_key"] == "***"
    assert out["nested"]["password"] == "***"
    assert out["nested"]["ok"] == "yes"
    assert out["message"] == "hello"
