"""Envia conhecimento processado para o webhook /ingest do KernelBots."""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

import httpx


def _checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def send_to_webhook(
    *,
    slug: str,
    discipline: str,
    title: str,
    order: int,
    content: str,
    raw_text: str,
    source_url: str,
    webhook_url: str | None = None,
    secret: str | None = None,
) -> dict:
    """
    Monta o payload e envia POST para {webhook_url}/ingest.

    source_checksum é calculado do raw_text (antes do processamento por IA),
    garantindo que mudanças na fonte original disparem atualização.

    Retorna o JSON de resposta: {"id": ..., "status": "ok"|"unchanged"}
    """
    webhook_url = (webhook_url or os.environ["WEBHOOK_URL"]).rstrip("/")
    secret = secret or os.environ["INGEST_SECRET"]

    payload = {
        "slug": slug,
        "discipline": discipline,
        "title": title,
        "order": order,
        "content": content,
        "source_checksum": _checksum(raw_text),
        "payload": {
            "url": source_url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "source_type": "transcription",
            "raw_length": len(raw_text),
        },
    }

    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{webhook_url}/ingest", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
