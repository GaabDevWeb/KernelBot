"""Streaming SSE para OpenRouter com fallback entre modelos."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncGenerator

import httpx

from core.config import Settings
from engine.context import ContextTrace

log = logging.getLogger(f"kernelbots.{__name__}")


class ChatProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def stream_response(
        self,
        messages: list[dict],
        trace: ContextTrace | None = None,
    ) -> AsyncGenerator[str, None]:
        payload_base = {
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
        }
        models = list(self._settings.models)
        timeout = self._settings.http_timeout

        if trace is not None:
            meta = {
                "v": 1,
                "label": trace.label,
                "sources": list(trace.sources),
                "pinned_active": trace.pinned_active,
                "pinned_display": trace.pinned_display,
            }
            yield f"data: [ACL_META]{json.dumps(meta, ensure_ascii=False)}\n\n"

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt, model in enumerate(models, start=1):
                try:
                    log.info(f"🤖 Tentativa {attempt}/{len(models)} — modelo: {model}")
                    t_start = time.perf_counter()
                    token_count = 0

                    async with client.stream(
                        "POST",
                        self._settings.openrouter_base,
                        headers=self._settings.openrouter_headers,
                        json={**payload_base, "model": model},
                    ) as response:

                        if response.status_code == 429:
                            log.warning(f"   ⏳ Rate limit (429) em '{model}' — acionando fallback...")
                            continue

                        if response.status_code >= 400:
                            body = await response.aread()
                            log.error(
                                f"   ❌ HTTP {response.status_code} em '{model}' — "
                                f"resposta: {body[:300].decode('utf-8', errors='replace')}"
                            )
                            continue

                        log.info(f"   ✅ Conexão estabelecida com '{model}' — iniciando stream...")

                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            raw = line[6:]
                            if raw.strip() == "[DONE]":
                                elapsed = (time.perf_counter() - t_start) * 1000
                                log.info(
                                    f"   🏁 Stream finalizado — modelo: '{model}' | "
                                    f"{token_count} token(s) | {elapsed:.0f}ms"
                                )
                                yield "data: [DONE]\n\n"
                                return

                            try:
                                chunk = json.loads(raw)
                                token: str = chunk["choices"][0].get("delta", {}).get("content") or ""
                                if token:
                                    token_count += 1
                                    safe = token.replace("\n", "\\n")
                                    yield f"data: {safe}\n\n"
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue

                        elapsed = (time.perf_counter() - t_start) * 1000
                        log.info(
                            f"   🏁 Stream finalizado (EOF) — modelo: '{model}' | "
                            f"{token_count} token(s) | {elapsed:.0f}ms"
                        )
                        yield "data: [DONE]\n\n"
                        return

                except httpx.TimeoutException:
                    log.warning(f"   ⏰ Timeout ({timeout:.0f}s) em '{model}' — acionando próximo fallback...")
                    continue
                except Exception as e:
                    log.exception(f"   💥 Erro inesperado em '{model}': {type(e).__name__}: {e}")
                    continue

        msg = "Todos os modelos de fallback falharam. Tente novamente mais tarde."
        log.error(f"🚨 {msg} | Modelos tentados: {', '.join(models)}")
        yield f"data: [ERROR] {msg}\n\n"
