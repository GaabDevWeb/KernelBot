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
from core.structured_log import ACL_MOD_PROVIDER, log_event
from engine.context import ContextTrace, hard_stop_message
from engine.disambiguation_parse import (
    candidates_from_retrieval,
    parse_ambiguity_options,
    strip_ambiguity_markup,
)
from engine.retrieval import (
    RetrievalDecision,
    anchored_post_generation_advisory_flags,
    post_generation_flags,
)

log = logging.getLogger(f"kernelbots.{__name__}")


def _normalize_hard_stop_payload(reason: str, payload: dict | None) -> dict | None:
    """Garante payload ACL_META completo para hard stops estruturados."""
    if not isinstance(payload, dict):
        return None
    out = dict(payload)
    if reason == "index_gap":
        out["suggested_candidates"] = (
            list(out["suggested_candidates"])
            if isinstance(out.get("suggested_candidates"), list)
            else []
        )
    elif reason == "ambiguous_retrieval":
        out["expected_lesson"] = None
        out["suggested_candidates"] = (
            list(out["suggested_candidates"])
            if isinstance(out.get("suggested_candidates"), list)
            else []
        )
    return out


def _build_meta(
    trace: ContextTrace | None,
    llm_called: bool,
    tokens_used: int,
    *,
    grounding_policy: str | None = None,
) -> dict:
    meta: dict = {"v": 3}
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
    allow_generation = trace.decision == "answer"
    meta.update(
        {
            "label": trace.label,
            "sources": list(trace.sources),
            "pinned_active": trace.pinned_active,
            "pinned_display": trace.pinned_display,
            "pin_chunks_used": trace.pin_chunks_used,
            "mode": trace.mode,
            "decision": trace.decision,
            "reason": trace.reason,
            "confidence": trace.confidence,
            "allow_generation": allow_generation,
            "llm_called": llm_called,
            "tokens_used": tokens_used,
        }
    )
    if trace.decision == "hard_stop":
        meta["catalog_match"] = bool(trace.catalog_match)
        payload = _normalize_hard_stop_payload(trace.reason, trace.hard_stop_payload)
        if payload is not None:
            meta["payload"] = payload
    if grounding_policy is not None:
        meta["grounding_policy"] = grounding_policy
    if trace.pinned_scope_key:
        meta["pinned_scope_key"] = trace.pinned_scope_key
    if trace.scope_hint:
        meta["scope_hint"] = trace.scope_hint
    if trace.suggested_scope_command:
        meta["suggested_scope_command"] = trace.suggested_scope_command
    if trace.sources_note:
        meta["sources_note"] = trace.sources_note
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


def _cursor_prompt_from_messages(messages: list[dict]) -> str:
    """Converte mensagens (estilo OpenAI chat) para um prompt único no Cursor SDK."""
    parts: list[str] = []
    for m in messages:
        role = str(m.get("role") or "").strip().lower()
        content = str(m.get("content") or "")
        if not content:
            continue
        if role == "system":
            parts.append("SYSTEM:\n" + content)
        elif role == "user":
            parts.append("USER:\n" + content)
        elif role == "assistant":
            parts.append("ASSISTANT:\n" + content)
        else:
            parts.append(f"{role.upper() or 'MESSAGE'}:\n{content}")
    return "\n\n".join(parts).strip()


class ChatProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _stream_meta(
        self,
        trace: ContextTrace | None,
        *,
        llm_called: bool,
        tokens_used: int,
    ) -> dict:
        return _build_meta(
            trace,
            llm_called,
            tokens_used,
            grounding_policy=self._settings.grounding_policy,
        )

    async def stream_response(
        self,
        messages: list[dict],
        trace: ContextTrace | None = None,
        decision: RetrievalDecision | None = None,
    ) -> AsyncGenerator[str, None]:
        if self._settings.llm_provider == "cursor":
            async for piece in self._stream_cursor(messages, trace=trace, decision=decision):
                yield piece
            return

        # --- Hard stop: não chama LLM ----------------------------------------
        is_hard_stop = trace is not None and trace.decision == "hard_stop"
        if is_hard_stop:
            meta = self._stream_meta(trace, llm_called=False, tokens_used=0)
            yield _sse_meta(meta)
            hard_text = ""
            # A última mensagem (assistant) carrega a resposta pré-montada.
            if messages and messages[-1].get("role") == "assistant":
                hard_text = str(messages[-1].get("content") or "")
            if not hard_text:
                hard_text = hard_stop_message(trace.reason)
            log_event(
                log,
                logging.INFO,
                ACL_MOD_PROVIDER,
                "llm_skipped_hard_stop",
                "stream sem LLM (hard stop retrieval)",
                metadata={
                    "reason": trace.reason,
                    "confidence": trace.confidence,
                    "mode": trace.mode,
                    "llm_called": False,
                    "tokens_used": 0,
                },
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
        initial_meta = self._stream_meta(trace, llm_called=True, tokens_used=0)
        yield _sse_meta(initial_meta)

        full_answer: list[str] = []

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt, model in enumerate(models, start=1):
                try:
                    log_event(
                        log,
                        logging.INFO,
                        ACL_MOD_PROVIDER,
                        "llm_attempt",
                        "tentativa de stream OpenRouter",
                        metadata={
                            "attempt": attempt,
                            "attempts_total": len(models),
                            "model": model,
                        },
                    )
                    t_start = time.perf_counter()
                    token_count = 0

                    async with client.stream(
                        "POST",
                        self._settings.openrouter_base,
                        headers=self._settings.openrouter_headers,
                        json={**payload_base, "model": model},
                    ) as response:

                        if response.status_code == 429:
                            log_event(
                                log,
                                logging.WARNING,
                                ACL_MOD_PROVIDER,
                                "llm_rate_limited",
                                "HTTP 429 — fallback para proximo modelo",
                                metadata={"model": model, "status_code": 429},
                            )
                            continue

                        if response.status_code >= 400:
                            body = await response.aread()
                            log_event(
                                log,
                                logging.ERROR,
                                ACL_MOD_PROVIDER,
                                "llm_http_error",
                                "resposta HTTP de erro do OpenRouter",
                                metadata={
                                    "model": model,
                                    "status_code": response.status_code,
                                    "body_preview": body[:300].decode("utf-8", errors="replace"),
                                },
                            )
                            continue

                        log_event(
                            log,
                            logging.INFO,
                            ACL_MOD_PROVIDER,
                            "llm_stream_opened",
                            "stream SSE iniciado",
                            metadata={"model": model},
                        )

                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            raw = line[6:]
                            if raw.strip() == "[DONE]":
                                elapsed = (time.perf_counter() - t_start) * 1000
                                log_event(
                                    log,
                                    logging.INFO,
                                    ACL_MOD_PROVIDER,
                                    "llm_stream_complete",
                                    "stream finalizado ([DONE])",
                                    metadata={
                                        "model": model,
                                        "tokens_used": token_count,
                                        "elapsed_ms": round(elapsed, 1),
                                    },
                                )
                                answer_text = "".join(full_answer)
                                async for piece in self._finalize_generation_meta(
                                    answer_text, trace, decision, token_count,
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
                        log_event(
                            log,
                            logging.INFO,
                            ACL_MOD_PROVIDER,
                            "llm_stream_complete_eof",
                            "stream terminou sem token [DONE]",
                            metadata={
                                "model": model,
                                "tokens_used": token_count,
                                "elapsed_ms": round(elapsed, 1),
                            },
                        )
                        answer_text = "".join(full_answer)
                        async for piece in self._finalize_generation_meta(
                            answer_text, trace, decision, token_count,
                        ):
                            yield piece
                        yield "data: [DONE]\n\n"
                        return

                except httpx.TimeoutException:
                    log_event(
                        log,
                        logging.WARNING,
                        ACL_MOD_PROVIDER,
                        "llm_timeout",
                        "timeout httpx — fallback",
                        metadata={"model": model, "timeout_s": timeout},
                    )
                    continue
                except Exception as e:
                    log_event(
                        log,
                        logging.ERROR,
                        ACL_MOD_PROVIDER,
                        "llm_exception",
                        f"excecao no stream: {type(e).__name__}",
                        metadata={"model": model, "error": str(e)},
                    )
                    log.exception("llm_exception detail")
                    continue

        # Todos os modelos falharam: mantém UX amigável e separa do hard stop
        # de retrieval via meta atualizada.
        friendly = hard_stop_message("provider_error")
        failure_meta = self._stream_meta(trace, llm_called=False, tokens_used=0)
        failure_meta.update({"decision": "hard_stop", "reason": "provider_error", "confidence": "low"})
        yield _sse_meta(failure_meta)
        log_event(
            log,
            logging.ERROR,
            ACL_MOD_PROVIDER,
            "llm_all_models_failed",
            "todos os modelos falharam — provider_error ao cliente",
            metadata={"models_tried": list(models)},
        )
        for piece in _sse_text_chunk(friendly):
            yield piece
        yield "data: [DONE]\n\n"

    async def _stream_cursor(
        self,
        messages: list[dict],
        *,
        trace: ContextTrace | None,
        decision: RetrievalDecision | None,
    ) -> AsyncGenerator[str, None]:
        # --- Hard stop: não chama LLM ----------------------------------------
        is_hard_stop = trace is not None and trace.decision == "hard_stop"
        if is_hard_stop:
            meta = self._stream_meta(trace, llm_called=False, tokens_used=0)
            yield _sse_meta(meta)
            hard_text = ""
            if messages and messages[-1].get("role") == "assistant":
                hard_text = str(messages[-1].get("content") or "")
            if not hard_text:
                hard_text = hard_stop_message(trace.reason)
            log_event(
                log,
                logging.INFO,
                ACL_MOD_PROVIDER,
                "llm_skipped_hard_stop",
                "stream sem LLM (hard stop retrieval)",
                metadata={
                    "reason": trace.reason,
                    "confidence": trace.confidence,
                    "mode": trace.mode,
                    "llm_called": False,
                    "tokens_used": 0,
                },
            )
            for piece in _sse_text_chunk(hard_text):
                yield piece
            yield "data: [DONE]\n\n"
            return

        initial_meta = self._stream_meta(trace, llm_called=True, tokens_used=0)
        yield _sse_meta(initial_meta)

        prompt = _cursor_prompt_from_messages(messages)
        full_answer: list[str] = []
        token_count = 0

        try:
            from cursor_sdk import AsyncClient, LocalAgentOptions
            from cursor_sdk.errors import CursorAgentError
        except Exception as e:
            # Dependência ausente ou import falhou: degrade para provider_error.
            friendly = hard_stop_message("provider_error")
            failure_meta = self._stream_meta(trace, llm_called=False, tokens_used=0)
            failure_meta.update({"decision": "hard_stop", "reason": "provider_error", "confidence": "low"})
            yield _sse_meta(failure_meta)
            log_event(
                log,
                logging.ERROR,
                ACL_MOD_PROVIDER,
                "cursor_sdk_import_error",
                f"falha ao importar cursor-sdk: {type(e).__name__}",
                metadata={"error": str(e)},
            )
            for piece in _sse_text_chunk(friendly):
                yield piece
            yield "data: [DONE]\n\n"
            return

        t_start = time.perf_counter()
        try:
            async with await AsyncClient.launch_bridge(workspace=str(self._settings.project_root)) as client:
                async with await client.agents.create(
                    model=self._settings.cursor_model,
                    api_key=self._settings.cursor_api_key,
                    local=LocalAgentOptions(cwd=str(self._settings.project_root)),
                ) as agent:
                    run = await agent.send(prompt)
                    async for chunk in run.iter_text():
                        if not chunk:
                            continue
                        token_count += 1
                        full_answer.append(chunk)
                        safe = chunk.replace("\n", "\\n")
                        yield f"data: {safe}\n\n"

                    result = await run.wait()
                    elapsed = (time.perf_counter() - t_start) * 1000
                    log_event(
                        log,
                        logging.INFO,
                        ACL_MOD_PROVIDER,
                        "llm_stream_complete",
                        "stream Cursor SDK finalizado",
                        metadata={
                            "model": self._settings.cursor_model,
                            "status": getattr(result, "status", None),
                            "tokens_used": token_count,
                            "elapsed_ms": round(elapsed, 1),
                        },
                    )
        except CursorAgentError as e:
            log_event(
                log,
                logging.ERROR,
                ACL_MOD_PROVIDER,
                "cursor_sdk_error",
                f"erro no Cursor SDK: {getattr(e, 'code', None) or type(e).__name__}",
                metadata={
                    "error": str(e),
                    "is_retryable": bool(getattr(e, "is_retryable", False)),
                    "code": getattr(e, "code", None),
                },
            )
            friendly = hard_stop_message("provider_error")
            failure_meta = self._stream_meta(trace, llm_called=False, tokens_used=0)
            failure_meta.update({"decision": "hard_stop", "reason": "provider_error", "confidence": "low"})
            yield _sse_meta(failure_meta)
            for piece in _sse_text_chunk(friendly):
                yield piece
            yield "data: [DONE]\n\n"
            return
        except Exception as e:
            log_event(
                log,
                logging.ERROR,
                ACL_MOD_PROVIDER,
                "cursor_sdk_exception",
                f"excecao no stream Cursor SDK: {type(e).__name__}",
                metadata={"error": str(e)},
            )
            log.exception("cursor_sdk_exception detail")
            friendly = hard_stop_message("provider_error")
            failure_meta = self._stream_meta(trace, llm_called=False, tokens_used=0)
            failure_meta.update({"decision": "hard_stop", "reason": "provider_error", "confidence": "low"})
            yield _sse_meta(failure_meta)
            for piece in _sse_text_chunk(friendly):
                yield piece
            yield "data: [DONE]\n\n"
            return

        answer_text = "".join(full_answer)
        async for piece in self._finalize_generation_meta(answer_text, trace, decision, token_count):
            yield piece
        yield "data: [DONE]\n\n"

    # --- Meta pós-stream: desambiguação estruturada + sanity check ---------

    async def _finalize_generation_meta(
        self,
        answer_text: str,
        trace: ContextTrace | None,
        decision: RetrievalDecision | None,
        tokens_used: int,
    ) -> AsyncGenerator[str, None]:
        """Override pós-geração primeiro; chips estruturados só se a resposta passar."""
        override_emitted = False
        async for piece in self._maybe_override_post_generation(
            answer_text, trace, decision, tokens_used,
        ):
            override_emitted = True
            yield piece
        if override_emitted:
            return
        async for piece in self._maybe_emit_disambiguation_meta(
            answer_text, trace, decision, tokens_used,
        ):
            yield piece

    async def _maybe_emit_disambiguation_meta(
        self,
        answer_text: str,
        trace: ContextTrace | None,
        decision: RetrievalDecision | None,
        tokens_used: int,
    ) -> AsyncGenerator[str, None]:
        if trace is None or decision is None:
            return
        if trace.reason != "ambiguous_retrieval" or not decision.allow_generation:
            return

        _, parsed = strip_ambiguity_markup(answer_text)
        options = parsed or parse_ambiguity_options(answer_text)
        if not options:
            from engine.disambiguation_parse import parse_incomplete_ambiguity_options

            options = parse_incomplete_ambiguity_options(answer_text)
        if not options and decision.selected_candidates:
            options = candidates_from_retrieval(decision.selected_candidates)
        if not options:
            return

        payload = {"expected_lesson": None, "suggested_candidates": options}
        updated = self._stream_meta(trace, llm_called=True, tokens_used=tokens_used)
        updated["disambiguation_options"] = options
        updated["payload"] = _normalize_hard_stop_payload("ambiguous_retrieval", payload)
        log_event(
            log,
            logging.INFO,
            ACL_MOD_PROVIDER,
            "disambiguation_options_meta",
            "opções estruturadas detectadas na resposta",
            metadata={"count": len(options)},
        )
        yield _sse_meta(updated)

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
        if not decision.allow_generation:
            return
        if not decision.selected_candidates:
            return
        policy = self._settings.grounding_policy
        flags = post_generation_flags(
            answer_text,
            trace.retrieval_trace.informative_terms if trace.retrieval_trace else (),
            decision.selected_candidates,
            grounding_policy=policy,
            decision_reason=decision.reason,
        )
        if not flags:
            return

        updated_meta = self._stream_meta(trace, llm_called=True, tokens_used=tokens_used)

        if policy in ("anchored", "hybrid"):
            advisory_flags = anchored_post_generation_advisory_flags(flags, answer_text)
            if not advisory_flags:
                return
            log_event(
                log,
                logging.INFO,
                ACL_MOD_PROVIDER,
                "post_generation_advisory",
                "sanity pos-geracao — aviso sem override (anchored/hybrid)",
                metadata={"flags": advisory_flags, "tokens_used": tokens_used},
            )
            updated_meta.update(
                {
                    "post_generation_advisory": True,
                    "post_generation_flags": advisory_flags,
                }
            )
            yield _sse_meta(updated_meta)
            return

        log_event(
            log,
            logging.WARNING,
            ACL_MOD_PROVIDER,
            "post_generation_override",
            "sanity pos-geracao — resposta substituida",
            metadata={
                "flags": list(flags),
                "reason": "post_generation_misalignment",
                "tokens_used": tokens_used,
            },
        )
        updated_meta.update(
            {
                "decision": "hard_stop",
                "reason": "post_generation_misalignment",
                "confidence": "low",
                "allow_generation": False,
                "post_generation_override": True,
                "misalignment": True,
                "post_generation_flags": flags,
            }
        )
        yield _sse_meta(updated_meta)
        override_text = (
            "\n\n---\n\n"
            + hard_stop_message("post_generation_misalignment")
        )
        for piece in _sse_text_chunk(override_text):
            yield piece
