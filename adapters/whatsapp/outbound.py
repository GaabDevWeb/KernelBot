"""Adapter WhatsApp outbound — Kernel → Orbit internal HTTP."""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger("kernelbots.adapters.whatsapp")


def orbit_outbound_base() -> str:
    return (os.getenv("ORBIT_INTERNAL_URL") or "http://127.0.0.1:8010").rstrip("/")


def _token() -> str:
    return (os.getenv("ACL_INTERNAL_BEARER_TOKEN") or "").strip()


async def outbound_status() -> dict[str, Any]:
    url = f"{orbit_outbound_base()}/internal/outbound/status"
    token = _token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                return r.json()
            return {"ok": False, "ready": False, "error": f"http_{r.status_code}"}
    except Exception as exc:
        return {"ok": False, "ready": False, "error": str(exc)[:200]}


async def send_message(
    *,
    to: str,
    text: str,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    attachments: lista de dicts com keys filename, mime, path (local file).
    O adapter lê o ficheiro e envia base64 ao Orbit (sem path partilhado).
    """
    token = _token()
    if not token:
        return {"ok": False, "error": "ACL_INTERNAL_BEARER_TOKEN missing"}

    payload_atts: list[dict[str, Any]] = []
    for att in attachments or []:
        path = Path(str(att.get("path") or ""))
        if not path.is_file():
            return {"ok": False, "error": f"attachment_missing:{path.name}"}
        data = path.read_bytes()
        payload_atts.append(
            {
                "filename": att.get("filename") or path.name,
                "mime": att.get("mime") or att.get("content_type") or "application/octet-stream",
                "data_base64": base64.b64encode(data).decode("ascii"),
            }
        )

    url = f"{orbit_outbound_base()}/internal/outbound/send"
    body = {"to": to, "text": text, "caption": text, "attachments": payload_atts}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code >= 400:
            return {
                "ok": False,
                "error": data.get("error") or f"http_{r.status_code}",
                "detail": data.get("detail"),
                "status_code": r.status_code,
            }
        return data if isinstance(data, dict) else {"ok": True, "raw": data}
    except Exception as exc:
        log.warning("whatsapp outbound failed: %s", exc)
        return {"ok": False, "error": "adapter_exception", "detail": str(exc)[:300]}
