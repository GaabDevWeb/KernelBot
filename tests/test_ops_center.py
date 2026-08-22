"""Testes P0 — Central de Operações."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.factory import create_app
from api.rate_limit import reset_for_tests
from kernel.ops.charts import svg_bar_chart, svg_line_chart
from kernel.trace import reset_trace_bus_for_tests
from kernel.trace.store import TraceStore


def test_svg_charts_render():
    bar = svg_bar_chart([1, 3, 2], label="msgs")
    assert "<svg" in bar and "msgs" in bar
    line = svg_line_chart([10, None, 30], label="lat")
    assert "<svg" in line and "polyline" in line


def test_hourly_series(tmp_path: Path):
    # Timestamps relativos ao agora: a janela de `hourly_series(hours=24)` é
    # calculada sobre o relógio real, e timestamps fixos expiram com o tempo.
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    ts1 = (now - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    ts2 = (now - timedelta(minutes=9)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    db = tmp_path / "t.sqlite3"
    store = TraceStore(db)
    store.insert_event(
        trace_id="t1",
        timestamp=ts1,
        service="kernel",
        stage="REQUEST",
        data={},
        priority=10,
    )
    store.insert_event(
        trace_id="t1",
        timestamp=ts2,
        service="kernel",
        stage="RESPONSE",
        data={},
        priority=10,
    )
    series = store.hourly_series(hours=24)
    assert isinstance(series, list)
    assert len(series) >= 1
    assert sum(b.messages for b in series) >= 1


def test_ops_login_and_dashboard(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", "ops-test-token-xyz")
    monkeypatch.setenv("ACL_TRACE_DB_PATH", str(tmp_path / "traces.sqlite3"))
    monkeypatch.delenv("ENV", raising=False)
    reset_for_tests()
    reset_trace_bus_for_tests()

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/ops/dashboard", follow_redirects=False)
        assert r.status_code == 303
        assert "/ops/login" in r.headers.get("location", "")

        bad = client.post("/ops/login", data={"token": "wrong"}, follow_redirects=False)
        assert bad.status_code == 401

        ok = client.post("/ops/login", data={"token": "ops-test-token-xyz"}, follow_redirects=False)
        assert ok.status_code == 303
        assert "/ops/dashboard" in ok.headers.get("location", "")

        dash = client.get("/ops/dashboard")
        assert dash.status_code == 200
        assert b"Dashboard" in dash.content
        assert b"Mensagens hoje" in dash.content

        for path in ("/ops/logs", "/ops/system", "/ops/metrics", "/ops/knowledge/rag"):
            resp = client.get(path)
            assert resp.status_code == 200, path

    reset_trace_bus_for_tests()
    reset_for_tests()
