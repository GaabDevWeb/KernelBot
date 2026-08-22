"""Testes Comunicações — store, security, UI auth."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.factory import create_app
from kernel.comms.security import AttachmentRejected, render_template, validate_upload
from kernel.comms.store import CommsStore, reset_comms_store_for_tests
from kernel.trace import reset_trace_bus_for_tests


def test_render_template_vars():
    out = render_template("Aula às {hora}: {link}", {"hora": "19h", "link": "https://x"})
    assert "19h" in out and "https://x" in out


def test_validate_upload_blocks_exe():
    try:
        validate_upload(filename="x.exe", size=10)
        assert False, "should reject"
    except AttachmentRejected:
        pass
    safe, mime = validate_upload(filename="aula.pdf", size=100, content_type="application/pdf")
    assert safe.endswith(".pdf")
    assert "pdf" in mime


def test_comms_store_campaign_flow(tmp_path: Path):
    store = CommsStore(tmp_path / "c.sqlite3")
    store.seed_default_templates()
    assert len(store.list_templates()) >= 3
    aid = store.create_audience(name="Turma Python")
    store.add_audience_member(aid, member_type="user", member_ref="5511999@s.whatsapp.net")
    cid = store.create_campaign(
        title="Aula",
        body="oi",
        channel="whatsapp",
        dest_type="audience",
        dest_ref=aid,
        status="draft",
        preview_text="oi",
    )
    camp = store.get_campaign(cid)
    assert camp is not None
    assert camp.title == "Aula"
    store.audit("create_campaign", campaign_id=cid)
    store.add_delivery(campaign_id=cid, dest_ref="x", dest_type="user", status="sent")
    assert len(store.list_deliveries(cid)) == 1


def test_comms_ui_requires_auth(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", "comms-token-test")
    monkeypatch.setenv("ACL_COMM_DB_PATH", str(tmp_path / "comms.sqlite3"))
    monkeypatch.setenv("ACL_TRACE_DB_PATH", str(tmp_path / "traces.sqlite3"))
    reset_trace_bus_for_tests()
    reset_comms_store_for_tests()

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/ops/comms/campaigns", follow_redirects=False)
        assert r.status_code == 303
        client.post("/ops/login", data={"token": "comms-token-test"}, follow_redirects=False)
        page = client.get("/ops/comms/campaigns")
        assert page.status_code == 200
        assert b"Campanhas" in page.content
        for path in (
            "/ops/comms/templates",
            "/ops/comms/audiences",
            "/ops/comms/schedules",
            "/ops/comms/history",
            "/ops/comms/campaigns/new",
        ):
            assert client.get(path).status_code == 200, path

    reset_comms_store_for_tests()
    reset_trace_bus_for_tests()
