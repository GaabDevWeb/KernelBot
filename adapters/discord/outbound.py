"""Adapter Discord outbound — preparado (não activo)."""

from __future__ import annotations

from typing import Any


async def outbound_status() -> dict[str, Any]:
    return {"ok": False, "ready": False, "error": "discord_not_configured"}


async def send_message(
    *,
    to: str,
    text: str,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "discord_not_implemented",
        "detail": "Adapter Discord outbound ainda não activo.",
        "to": to,
        "chars": len(text or ""),
        "attachments": len(attachments or []),
    }
