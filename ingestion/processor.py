"""Processa transcrições brutas via OpenRouter e retorna JSON estruturado."""
from __future__ import annotations

import json
import os
import re

import httpx

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"
PROCESS_MODEL   = "nvidia/nemotron-3-super-120b-a12b:free"

_SYSTEM_PROMPT = (
    "Você é um organizador de conteúdo pedagógico. "
    "Dado o título e a transcrição de uma aula, retorne um objeto JSON com os seguintes campos:\n"
    '- "description": string de 1-2 frases resumindo o tema central da aula (obrigatório)\n'
    '- "content": string com o conteúdo completo organizado em markdown estruturado, '
    "com headers (##), seções claras, sem repetições nem ruído de fala (obrigatório)\n"
    '- "keywords": string com palavras-chave separadas por vírgula (opcional, pode ser null)\n'
    '- "learning_objectives": string listando os objetivos de aprendizagem separados por vírgula (opcional, pode ser null)\n'
    '- "concepts": string com conceitos principais separados por vírgula (opcional, pode ser null)\n'
    "Responda APENAS com o JSON, sem markdown, sem explicações adicionais."
)


def _extract_json(text: str) -> dict:
    """Extrai JSON do texto da resposta, tolerando markdown code fences."""
    text = text.strip()
    # Remove ```json ... ``` ou ``` ... ```
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fenced:
        text = fenced.group(1).strip()
    return json.loads(text)


async def process_transcription(
    raw_text: str,
    title: str,
    api_key: str | None = None,
    model: str = PROCESS_MODEL,
) -> dict:
    """
    Envia a transcrição bruta ao OpenRouter e retorna dict estruturado.

    Retorna: {description, content, keywords, learning_objectives, concepts}
    """
    api_key = api_key or os.environ["OPENROUTER_API_KEY"]

    user_content = f"# {title}\n\n{raw_text}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ],
        "response_format": {"type": "json_object"},
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
        raw_content = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Resposta inesperada do OpenRouter: {data}") from exc

    try:
        result = _extract_json(raw_content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"OpenRouter não retornou JSON válido: {raw_content[:300]}"
        ) from exc

    if not result.get("description") or not result.get("content"):
        raise RuntimeError(
            f"Campos obrigatórios ausentes na resposta do OpenRouter: {list(result.keys())}"
        )

    return {
        "description":         str(result["description"]).strip(),
        "content":             str(result["content"]).strip(),
        "keywords":            str(result["keywords"]).strip() if result.get("keywords") else None,
        "learning_objectives": str(result["learning_objectives"]).strip() if result.get("learning_objectives") else None,
        "concepts":            str(result["concepts"]).strip() if result.get("concepts") else None,
    }
