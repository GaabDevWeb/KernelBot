"""Serviço de Comunicações — campanhas, expansão de públicos, dispatch, auditoria."""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import zipfile
from pathlib import Path
from typing import Any

from adapters.discord import outbound as discord_out
from adapters.whatsapp import outbound as whatsapp_out
from kernel.comms.security import (
    AttachmentRejected,
    render_template,
    sha256_bytes,
    validate_upload,
)
from kernel.comms.store import Campaign, CommsStore, get_comms_store
from kernel.trace import emit_kernel, new_trace_id

log = logging.getLogger("kernelbots.comms")


def operator_jid() -> str:
    return (
        os.getenv("ACL_COMM_OPERATOR_JID")
        or os.getenv("COMM_OPERATOR_JID")
        or ""
    ).strip()


def attachments_root() -> Path:
    raw = (os.getenv("ACL_COMM_ATTACHMENTS_DIR") or "data/comms/attachments").strip()
    p = Path(raw).expanduser()
    if not p.is_absolute():
        root = Path(__file__).resolve().parent.parent.parent
        p = root / p
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def resolve_preview(body: str, variables: dict[str, str] | None = None) -> str:
    return render_template(body, variables)


def expand_destinations(store: CommsStore, campaign: Campaign) -> list[tuple[str, str]]:
    """Retorna lista (dest_type, dest_ref)."""
    if campaign.dest_type == "audience":
        members = store.list_audience_members(campaign.dest_ref)
        return [(m["member_type"], m["member_ref"]) for m in members]
    return [(campaign.dest_type, campaign.dest_ref)]


async def _send_one(
    *,
    channel: str,
    dest_type: str,
    dest_ref: str,
    text: str,
    attachment_meta: list[dict[str, Any]],
) -> dict[str, Any]:
    if channel == "discord":
        return await discord_out.send_message(to=dest_ref, text=text, attachments=attachment_meta)
    # whatsapp default
    return await whatsapp_out.send_message(to=dest_ref, text=text, attachments=attachment_meta)


def _attachment_payload(store: CommsStore, campaign_id: str) -> list[dict[str, Any]]:
    out = []
    for att in store.list_campaign_attachments(campaign_id):
        out.append(
            {
                "filename": att["filename"],
                "mime": att["content_type"],
                "path": att["storage_path"],
                "content_type": att["content_type"],
            }
        )
    return out


async def execute_campaign(
    campaign_id: str,
    *,
    force_dest: tuple[str, str] | None = None,
    mark_status: bool = True,
) -> dict[str, Any]:
    store = get_comms_store()
    if store is None:
        return {"ok": False, "error": "store_unavailable"}
    campaign = store.get_campaign(campaign_id)
    if campaign is None:
        return {"ok": False, "error": "not_found"}
    if campaign.status == "cancelled":
        return {"ok": False, "error": "cancelled"}

    prev_status = campaign.status
    trace_id = new_trace_id()
    emit_kernel(
        "COMM_SEND_START",
        trace_id=trace_id,
        data={"campaign_id": campaign_id, "channel": campaign.channel, "title": campaign.title},
    )
    store.audit("execute_send", campaign_id=campaign_id, detail={"trace_id": trace_id}, trace_id=trace_id)
    if mark_status:
        store.update_campaign_status(campaign_id, "sending")

    dests = [force_dest] if force_dest else expand_destinations(store, campaign)
    if not dests:
        if mark_status:
            store.update_campaign_status(campaign_id, "failed")
        store.audit("send_failed", campaign_id=campaign_id, detail={"reason": "no_destinations"}, trace_id=trace_id)
        return {"ok": False, "error": "no_destinations"}

    atts = _attachment_payload(store, campaign_id)
    text = campaign.preview_text or campaign.body
    ok_n = 0
    fail_n = 0
    for dest_type, dest_ref in dests:
        result = await _send_one(
            channel=campaign.channel,
            dest_type=dest_type,
            dest_ref=dest_ref,
            text=text,
            attachment_meta=atts,
        )
        success = bool(result.get("ok"))
        store.add_delivery(
            campaign_id=campaign_id,
            dest_ref=dest_ref,
            dest_type=dest_type,
            status="sent" if success else "failed",
            error="" if success else str(result.get("error") or result.get("detail") or "fail"),
            latency_ms=result.get("latency_ms"),
            adapter=result,
        )
        if success:
            ok_n += 1
        else:
            fail_n += 1
            emit_kernel(
                "COMM_SEND_FAIL",
                trace_id=trace_id,
                data={"campaign_id": campaign_id, "dest": dest_ref, "error": result.get("error")},
            )

    if mark_status:
        final = "sent" if ok_n and not fail_n else ("failed" if not ok_n else "sent")
        store.update_campaign_status(campaign_id, final)
    else:
        final = prev_status
        store.update_campaign_status(campaign_id, prev_status)

    store.audit(
        "send_complete",
        campaign_id=campaign_id,
        detail={"ok": ok_n, "failed": fail_n, "status": final, "test": not mark_status},
        trace_id=trace_id,
    )
    emit_kernel(
        "COMM_SEND_DONE",
        trace_id=trace_id,
        data={"campaign_id": campaign_id, "ok": ok_n, "failed": fail_n, "status": final},
    )
    return {"ok": fail_n == 0, "sent": ok_n, "failed": fail_n, "status": final, "trace_id": trace_id}


async def send_test(campaign_id: str) -> dict[str, Any]:
    jid = operator_jid()
    if not jid:
        return {
            "ok": False,
            "error": "operator_jid_missing",
            "detail": "Defina ACL_COMM_OPERATOR_JID (JID ou número do operador).",
        }
    store = get_comms_store()
    if store is None:
        return {"ok": False, "error": "store_unavailable"}
    store.audit("send_test", campaign_id=campaign_id, detail={"to": jid})
    return await execute_campaign(campaign_id, force_dest=("user", jid), mark_status=False)


def save_upload(store: CommsStore, *, filename: str, data: bytes, content_type: str | None) -> str:
    safe, mime = validate_upload(filename=filename, size=len(data), content_type=content_type)
    digest = sha256_bytes(data)
    existing = store.get_attachment_by_sha(digest)
    if existing:
        return str(existing["id"])
    root = attachments_root()
    path = root / f"{digest}{Path(safe).suffix.lower()}"
    if not path.exists():
        path.write_bytes(data)
    return store.register_attachment(
        sha256=digest,
        filename=safe,
        content_type=mime,
        size_bytes=len(data),
        storage_path=str(path),
    )


def build_export_zip(store: CommsStore) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for table in (
            "comm_campaigns",
            "comm_templates",
            "comm_audiences",
            "comm_audience_members",
            "comm_deliveries",
            "comm_attachments",
            "comm_audit",
        ):
            rows = store.export_table(table)
            zf.writestr(f"{table}.json", json.dumps(rows, ensure_ascii=False, indent=2))
            # CSV
            if rows:
                out = io.StringIO()
                writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
                zf.writestr(f"{table}.csv", out.getvalue())
    return buf.getvalue()


__all__ = [
    "AttachmentRejected",
    "build_export_zip",
    "execute_campaign",
    "expand_destinations",
    "operator_jid",
    "resolve_preview",
    "save_upload",
    "send_test",
]
