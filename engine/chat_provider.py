"""Streaming SSE para OpenRouter com fallback entre modelos.

Mudanças vs versão anterior:

- Hard stop não chama LLM. Quando `trace.decision == "hard_stop"`, a última
  mensagem `assistant` é a resposta pronta e o provider só faz streaming
  dela, economizando tokens e evitando resposta confiante sem base.
- Sanity check pós-geração (Fase 3): depois que o modelo terminou, a
  resposta passa por `post_generation_flags`. Se houver flag e o modo for
  `strict`, a resposta enviada ao usuário é trocada por
  `post_generation_misalignment`.
- `ACL_META` agora também carrega `mode`, `decision`, `reason`, `confidence`
  e `llm_called`.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncGenerator

import httpx

from core.config import Settings
from engine.context import ContextTrace, hard_stop_message
from engine.retrieval import RetrievalDecision, post_generation_flags

log = logging.getLogger(f"kernelbots.{__name__}")


def _build_meta(trace: ContextTrace | None, llm_called: bool, tokens_used: int) -> dict:
    meta: dict = {"v": 2}
    if trace is None:
        meta.update(
            {
                "label": "Assistente geral",
                "sources": [],
                "pinned_active": False,
                "pinned_display": None,
                "mode": "strict",
                "decision": "answer",
                "reason": "ok",
                "confidence": "high",
                "llm_called": llm_called,
                "tokens_used": tokens_used,
            }
        )
        return meta
    meta.update(
        {
            "label": trace.label,
            "sources": list(trace.sources),
            "pinned_active": trace.pinned_active,
            "pinned_display": trace.pinned_display,
            "mode": trace.mode,
            "decision": trace.decision,
            "reason": trace.reason,
            "confidence": trace.confidence,
            "llm_called": llm_called,
            "tokens_used": tokens_used,
        }
    )
    return meta


def _sse_meta(meta: dict) -> str:
    return f"data: [ACL_META]{json.dumps(meta, ensure_ascii=False)}\n\n"


def _sse_text_chunk(text: str, chunk_size: int = 80) -> list[str]:
    """Divide texto em pedaços menores para streaming amigável (UI de chat)."""
    out: list[str] = []
    for i in range(0, len(text), chunk_size):
        piece = text[i : i + chunk_size]
        safe = piece.replace("\n", "\\n")
        out.append(f"data: {safe}\n\n")
    return out


class ChatProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def stream_response(
        self,
        messages: list[dict],
        trace: ContextTrace | None = None,
        decision: RetrievalDecision | None = None,
    ) -> AsyncGenerator[str, None]:
        # --- Hard stop: não chama LLM ----------------------------------------
        is_hard_stop = trace is not None and trace.decision == "hard_stop"
        if is_hard_stop:
            meta = _build_meta(trace, llm_called=False, tokens_used=0)
            yield _sse_meta(meta)
            hard_text = ""
            # A última mensagem (assistant) carrega a resposta pré-montada.
            if messages and messages[-1].get("role") == "assistant":
                hard_text = str(messages[-1].get("content") or "")
            if not hard_text:
                hard_text = hard_stop_message(trace.reason)
            log.info(
                "   🛑 Hard stop — reason=%s | confidence=%s | sem chamada ao LLM",
                trace.reason, trace.confidence,
            )
            for piece in _sse_text_chunk(hard_text):
                yield piece
            yield "data: [DONE]\n\n"
            return

        payload_base = {
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
        }
        models = list(self._settings.models)
        timeout = self._settings.http_timeout

        # Meta inicial indicando que pretendemos chamar o LLM. Na falha de
        # provider trocamos para decision=hard_stop no meta final via
        # mensagem [ACL_META_UPDATE] (mantido compatível: frontend ignora
        # prefixos desconhecidos).
        initial_meta = _build_meta(trace, llm_called=True, tokens_used=0)
        yield _sse_meta(initial_meta)

        full_answer: list[str] = []

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
                                async for piece in self._maybe_override_post_generation(
                                    "".join(full_answer), trace, decision, token_count,
                                ):
                                    yield piece
                                yield "data: [DONE]\n\n"
                                return

                            try:
                                chunk = json.loads(raw)
                                token: str = chunk["choices"][0].get("delta", {}).get("content") or ""
                                if token:
                                    token_count += 1
                                    full_answer.append(token)
                                    safe = token.replace("\n", "\\n")
                                    yield f"data: {safe}\n\n"
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue

                        elapsed = (time.perf_counter() - t_start) * 1000
                        log.info(
                            f"   🏁 Stream finalizado (EOF) — modelo: '{model}' | "
                            f"{token_count} token(s) | {elapsed:.0f}ms"
                        )
                        async for piece in self._maybe_override_post_generation(
                            "".join(full_answer), trace, decision, token_count,
                        ):
                            yield piece
                        yield "data: [DONE]\n\n"
                        return

                except httpx.TimeoutException:
                    log.warning(f"   ⏰ Timeout ({timeout:.0f}s) em '{model}' — acionando próximo fallback...")
                    continue
                except Exception as e:
                    log.exception(f"   💥 Erro inesperado em '{model}': {type(e).__name__}: {e}")
                    continue

        # Todos os modelos falharam: mantém UX amigável e separa do hard stop
        # de retrieval via meta atualizada.
        friendly = hard_stop_message("provider_error")
        failure_meta = _build_meta(trace, llm_called=False, tokens_used=0)
        failure_meta.update({"decision": "hard_stop", "reason": "provider_error", "confidence": "low"})
        yield _sse_meta(failure_meta)
        log.error(
            "🚨 Todos os modelos de fallback falharam | Modelos tentados: %s",
            ", ".join(models),
        )
        for piece in _sse_text_chunk(friendly):
            yield piece
        yield "data: [DONE]\n\n"

    # --- Fase 3: sanity check pós-geração ----------------------------------

    async def _maybe_override_post_generation(
        self,
        answer_text: str,
        trace: ContextTrace | None,
        decision: RetrievalDecision | None,
        tokens_used: int,
    ) -> AsyncGenerator[str, None]:
        """Aplica override para `post_generation_misalignment` se preciso.

        Executa apenas quando modo=strict, decisão original=answer e há
        candidatos selecionados. A resposta original já foi streamada,
        então enviamos um meta-update e uma mensagem clara de hard stop.
        """
        if trace is None or decision is None:
            return
        if trace.mode != "strict":
            return
        if not decision.allow_generation:
            return
        if not decision.selected_candidates:
            return
        flags = post_generation_flags(
            answer_text,
            trace.retrieval_trace.informative_terms if trace.retrieval_trace else (),
            decision.selected_candidates,
        )
        if not flags:
            return
        log.warning(
            "   🚨 Sanity check pós-geração: flags=%s — substituindo resposta por hard stop",
            flags,
        )
        updated_meta = _build_meta(trace, llm_called=True, tokens_used=tokens_used)
        updated_meta.update(
            {
                "decision": "hard_stop",
                "reason": "post_generation_misalignment",
                "confidence": "low",
                "post_generation_flags": flags,
            }
        )
        # Emite um separador textual para evitar que a resposta parcial já
        # mostrada fique sem aviso. Usamos meta novo + bloco textual claro.
        yield _sse_meta(updated_meta)
        override_text = (
            "\n\n---\n\n"
            + hard_stop_message("post_generation_misalignment")
        )
        for piece in _sse_text_chunk(override_text):
            yield piece
