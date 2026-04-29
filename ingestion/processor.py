"""Processa transcrições brutas via OpenRouter e retorna markdown estruturado."""
from __future__ import annotations

import os

import httpx

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"
PROCESS_MODEL   = "google/gemini-2.5-flash:free"

_SYSTEM_PROMPT = (
    "Você é um organizador de conteúdo pedagógico. "
    "Organize e resuma a transcrição de aula fornecida em markdown estruturado. "
    "Crie seções com headers (##), extraia conceitos-chave, elimine repetições "
    "e ruído de fala. Mantenha fidelidade ao conteúdo original. "
    "Responda apenas com o markdown, sem explicações adicionais."
)


async def process_transcription(
    raw_text: str,
    title: str,
    api_key: str | None = None,
    model: str = PROCESS_MODEL,
) -> str:
    """
    Envia a transcrição bruta ao OpenRouter e retorna o conteúdo processado.

    A chave API é lida de OPENROUTER_API_KEY se não fornecida.
    """
    api_key = api_key or os.environ["OPENROUTER_API_KEY"]

    user_content = f"# {title}\n\n{raw_text}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "KernelBots Ingestion",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(OPENROUTER_BASE, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Resposta inesperada do OpenRouter: {data}") from exc
