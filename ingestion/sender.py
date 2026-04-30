"""Envia conhecimento processado para o webhook /ingest do KernelBots."""
from __future__ import annotations

import os

import httpx


async def send_to_webhook(
    *,
    slug: str,
    discipline: str,
    title: str,
    order: int,
    processed: dict,
    webhook_url: str | None = None,
    secret: str | None = None,
) -> dict:
    """
    Monta o payload e envia POST para {webhook_url}/ingest.

    processed deve conter: description, content, e opcionalmente
    keywords, learning_objectives, concepts.

    Retorna o JSON de resposta: {"id": ..., "status": "inserted"|"updated"}
    """
    webhook_url = (webhook_url or os.environ["WEBHOOK_URL"]).rstrip("/")
    secret = secret or os.environ["INGEST_SECRET"]

    payload = {
        "slug":                slug,
        "discipline":          discipline,
        "title":               title,
        "order":               order,
        "description":         processed["description"],
        "content":             processed["content"],
        "keywords":            processed.get("keywords"),
        "learning_objectives": processed.get("learning_objectives"),
        "concepts":            processed.get("concepts"),
    }

    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{webhook_url}/ingest", json=payload, headers=headers)
        if response.is_error:
            raise RuntimeError(
                f"HTTP {response.status_code} — {response.text}"
            )
        return response.json()
