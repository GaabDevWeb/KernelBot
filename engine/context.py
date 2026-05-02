"""Montagem de mensagens (system + user) para o chat com RAG /doc /content.

Este módulo consome `engine.retrieval.build_decision` e monta o prompt
apenas quando a decisão permitir. Hard stop é tratado diretamente como
resposta ao usuário — não chama o LLM.

Mudanças vs versão anterior (plano rag_acl_incremental):

- `/content` NÃO injeta mais `scope_chunks[:5]`. Sem hit suficiente, vira
  hard stop com UX de reformulação.
- Pin NÃO ressuscita contexto desalinhado; se o pin existir e a decisão
  atual for hard stop por `insufficient_context`, o pin pode entrar como
  fonte adicional, mas apenas se a consulta tiver termos informativos
  mínimos e o trace continua hard stop caso retrieval falhe.
- `ContextTrace` ganha `mode`, `decision`, `reason`, `confidence` e a
  `RetrievalTrace` completa.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from core.config import Settings
from core.structured_log import ACL_MOD_CONTEXT, log_event
from engine.pinned_store import PinnedContext, PinnedSessionStore
from engine.retrieval import (
    RetrievalDecision,
    RetrievalTrace,
    build_decision,
    extract_informative_terms,
    select_mode,
)
from engine.search import SearchEngine

log = logging.getLogger(f"kernelbots.{__name__}")

# Mais longo primeiro; exige espaço ou fim após o prefixo (evita `/pythonfoo`).
_DISCIPLINE_COMMAND_PREFIXES: tuple[tuple[str, str], ...] = (
    ("/planejamento-curso-carreira", "planejamento-curso-carreira"),
    ("/visualizacao-sql", "visualizacao-sql"),
    ("/projeto-bloco", "projeto-bloco"),
    ("/python", "python"),
)

_TRACE_LABEL_BY_DISCIPLINE: dict[str, str] = {
    "python": "Python",
    "visualizacao-sql": "Visualização SQL",
    "projeto-bloco": "Projeto bloco",
    "planejamento-curso-carreira": "Planejamento de carreira",
    "doc": "Documentação (doc)",
    "geral": "Base geral",
}

_SOURCES_CAP = 20

_RESET_PREFIX_RE = re.compile(r"^/(?:reset|limpar)\s*", re.IGNORECASE)


# --- Mensagens UX padronizadas (Fase 1/3) -----------------------------------

_HARD_STOP_MESSAGES: dict[str, str] = {
    "insufficient_context": (
        "Não encontrei informação suficiente na base para responder com segurança.\n\n"
        "Tente especificar melhor, por exemplo incluindo tecnologia, contexto ou objetivo."
    ),
    "context_misaligned": (
        "Encontrei trechos na base, mas eles não cobrem bem a sua pergunta.\n\n"
        "Reformule incluindo termos mais específicos sobre o que quer saber."
    ),
    "underspecified_query": (
        "Sua pergunta está vaga para responder com segurança usando a base.\n\n"
        "Use o formato: [tecnologia] + [problema] + [contexto].\n\n"
        "Exemplos:\n"
        "- SQL + performance + query lenta\n"
        "- Docker + erro + build falhando\n"
        "- API + timeout + chamada de autenticação"
    ),
    "vague_but_high_risk": (
        "Sua pergunta pode ter várias interpretações e eu não tenho contexto suficiente "
        "para escolher uma com segurança.\n\n"
        "Reformule usando: [tecnologia] + [problema] + [contexto]."
    ),
    "ambiguous_retrieval": (
        "Encontrei conteúdos parecidos na base e não consegui distinguir qual deles "
        "realmente responde à sua pergunta.\n\n"
        "Adicione detalhes que ajudem a desempatar, como nome do módulo, comando ou tecnologia."
    ),
    "low_confidence": (
        "Encontrei conteúdo que lembra a sua pergunta, mas a confiança do retrieval ficou baixa "
        "e no modo estrito prefiro não arriscar uma resposta incorreta.\n\n"
        "Reformule com mais detalhes técnicos ou use um comando de escopo (`/doc`, `/python`, etc.)."
    ),
    "post_generation_misalignment": (
        "Preparei uma resposta com base nos trechos encontrados, mas a checagem final "
        "indicou que ela pode ter saído do escopo das fontes.\n\n"
        "Reformule a pergunta com termos mais próximos do material ou tente novamente."
    ),
    "provider_error": (
        "Tive um problema técnico ao contatar o modelo de linguagem.\n\n"
        "Tente novamente em alguns instantes. Se persistir, avise o responsável."
    ),
}


def hard_stop_message(reason: str) -> str:
    return _HARD_STOP_MESSAGES.get(
        reason,
        "Não consegui responder com segurança agora. Reformule a pergunta e tente novamente.",
    )


@dataclass(frozen=True)
class ContextTrace:
    """Metadados para UI: rótulo de contexto, fontes, pin, decisão e confiança."""

    label: str
    sources: tuple[str, ...]
    pinned_active: bool = False
    pinned_display: str | None = None
    mode: str = "strict"
    decision: str = "answer"
    reason: str = "ok"
    confidence: str = "high"
    retrieval_trace: RetrievalTrace | None = None


@dataclass(frozen=True)
class BuildMessagesResult:
    messages: list[dict]
    trace: ContextTrace
    decision: RetrievalDecision | None = None


def _dedupe_sources(sources: list[str], limit: int = _SOURCES_CAP) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for s in sources:
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= limit:
            break
    return tuple(out)


def _trace_label_for_discipline(disc_id: str) -> str:
    return _TRACE_LABEL_BY_DISCIPLINE.get(disc_id, disc_id.replace("-", " ").title())


def _global_scope_label(settings: Settings) -> str:
    if settings.global_context_mode == "all":
        return "Todas as disciplinas"
    return "Base geral"


def _match_discipline_command(user_message: str) -> tuple[str | None, str]:
    for prefix, disc_id in _DISCIPLINE_COMMAND_PREFIXES:
        if not user_message.startswith(prefix):
            continue
        tail = user_message[len(prefix) :]
        if tail and not tail[0].isspace():
            continue
        return disc_id, tail.strip()
    return None, user_message


def _strip_reset_command(user_message: str) -> tuple[str, bool]:
    """Remove `/reset` ou `/limpar` do início; devolve (mensagem_restante, foi_reset)."""
    s = user_message.strip()
    if not _RESET_PREFIX_RE.match(s):
        return user_message, False
    rest = _RESET_PREFIX_RE.sub("", s).strip()
    if not rest:
        rest = "(Pedido: contexto fixado foi removido. Confirma de forma breve.)"
    return rest, True


def _request_scope_key(
    force_doc: bool,
    force_rag: bool,
    discipline_from_command: str | None,
    json_discipline: str | None,
) -> str | None:
    if force_doc:
        return "doc"
    if force_rag and discipline_from_command is None:
        return "content"
    if discipline_from_command is not None:
        return f"discipline:{discipline_from_command}"
    if json_discipline is not None:
        return f"discipline:{json_discipline}"
    return None


def _pin_conflicts(pin: PinnedContext, request_scope_key: str | None) -> bool:
    if request_scope_key is None:
        return False
    return pin.scope_key != request_scope_key


def _discipline_from_pin_scope(pin: PinnedContext) -> str | None:
    if pin.scope_key.startswith("discipline:"):
        return pin.scope_key.split(":", 1)[1]
    return None


def _display_name_from_source(source: str) -> str:
    stem = Path(source.replace("\\", "/")).stem
    return stem.replace("-", " ").strip() or source


def _trim_pin_chunks(
    chunks: list[dict[str, str]],
    max_chars: int,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    total = 0
    for c in chunks:
        text = c.get("text") or ""
        src = c.get("source") or ""
        if total >= max_chars:
            break
        room = max_chars - total
        if len(text) <= room:
            out.append({"source": src, "text": text})
            total += len(text)
        elif room > 200:
            out.append({"source": src, "text": text[:room] + "\n[…truncado…]"})
            break
        else:
            break
    return out


def _join_chunks_for_prompt(selected: list[dict[str, str]]) -> str:
    return "\n\n---\n\n".join(
        f"[Fonte: {c['source']}]\n{c['text']}" for c in selected if c.get("text")
    )


_STRICT_GROUNDING_INSTRUCTION = (
    "Você possui acesso à seguinte base de conhecimento local. "
    "Responda APENAS com base nos trechos fornecidos. "
    "Se a resposta exigir qualquer informação que não esteja explicitamente nos trechos, "
    "responda que não há informação suficiente na base. "
    "Não faça suposições. Não complete lacunas com conhecimento geral.\n\n"
)


class ContextManager:
    def __init__(
        self,
        settings: Settings,
        search_engine: SearchEngine,
        pinned_store: PinnedSessionStore | None = None,
    ) -> None:
        self._settings = settings
        self._search_engine = search_engine
        self._pinned_store = pinned_store

    def _sanitize_discipline(self, raw: str | None) -> str | None:
        return self._search_engine.normalize_discipline(raw)

    def build_messages(
        self,
        user_message: str,
        discipline_filter: str | None = None,
        session_id: str | None = None,
    ) -> BuildMessagesResult:
        store = self._pinned_store
        sp = self._settings.system_prompt_geral

        raw_input = user_message.strip()
        did_reset = False
        if store and session_id:
            working, did_reset = _strip_reset_command(raw_input)
            if did_reset:
                store.clear(session_id)
                user_message = working
            else:
                user_message = raw_input
        else:
            user_message = raw_input

        force_doc = user_message.startswith("/doc")
        force_rag = user_message.startswith("/content")
        discipline_from_command: str | None = None
        query: str

        if force_doc:
            query = user_message.removeprefix("/doc").strip()
        elif force_rag:
            query = user_message.removeprefix("/content").strip()
        else:
            discipline_from_command, query = _match_discipline_command(user_message)
            if discipline_from_command is not None:
                force_rag = True

        json_discipline = self._sanitize_discipline(discipline_filter)
        request_scope = _request_scope_key(
            force_doc, force_rag, discipline_from_command, json_discipline
        )

        pin: PinnedContext | None = None
        if store and session_id:
            pin = store.get(session_id)
            if pin and _pin_conflicts(pin, request_scope):
                store.clear(session_id)
                pin = None
            store.begin_turn(session_id)
            pin = store.get(session_id)

        effective_discipline: str | None
        if discipline_from_command is not None:
            effective_discipline = self._sanitize_discipline(discipline_from_command)
        elif json_discipline is not None:
            effective_discipline = json_discipline
        elif request_scope is None and pin is not None:
            effective_discipline = self._sanitize_discipline(_discipline_from_pin_scope(pin))
        else:
            effective_discipline = None

        # Sempre `strict` nesta mitigação. `assistive` viria via flag
        # explícita de produto, que hoje não existe — fica como hook.
        mode = select_mode(
            force_doc=force_doc,
            force_rag=force_rag,
            discipline_from_command=discipline_from_command,
            has_explicit_assistive_flag=False,
        )

        log_event(
            log,
            logging.INFO,
            ACL_MOD_CONTEXT,
            "context_route",
            "pedido recebido — encaminhamento RAG",
            metadata={
                "user_message_chars": len(user_message),
                "query": query,
                "mode": mode,
                "force_rag": force_rag,
                "force_doc": force_doc,
                "effective_discipline": effective_discipline,
                "discipline_from_command": discipline_from_command,
                "did_reset": did_reset,
                "pin_active": bool(pin),
            },
        )

        # --- Caso /doc: injeção determinística do silo "doc".
        # Esse fluxo preserva o comportamento do comando `/doc` — ele já é
        # um "pin explícito" da documentação; a decisão de retrieval não se
        # aplica aqui porque a fonte é fixa.
        if force_doc:
            doc_chunks = [c for c in self._search_engine.chunks if c.get("discipline") == "doc"]
            if doc_chunks:
                log_event(
                    log,
                    logging.INFO,
                    ACL_MOD_CONTEXT,
                    "doc_injection",
                    "injecao deterministica silo doc",
                    metadata={"chunk_count": len(doc_chunks)},
                )
                ctx = _join_chunks_for_prompt(
                    [{"source": str(c["source"]), "text": str(c["text"])} for c in doc_chunks]
                )
                system_content = (
                    f"{sp}\n\n"
                    f"{_STRICT_GROUNDING_INSTRUCTION}"
                    f"{ctx}"
                )
                trace_sources = [str(c["source"]) for c in doc_chunks]
                pin_chunks = [{"source": str(c["source"]), "text": str(c["text"])} for c in doc_chunks]
                self._save_pin(session_id, "doc", pin_chunks, trace_sources)
                trace = ContextTrace(
                    label="Documentação (doc)",
                    sources=_dedupe_sources(trace_sources),
                    pinned_active=self._pin_active(session_id),
                    pinned_display=self._pin_display(session_id),
                    mode=mode,
                    decision="answer",
                    reason="ok",
                    confidence="high",
                )
                return BuildMessagesResult(
                    messages=[
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": query},
                    ],
                    trace=trace,
                )
            # Sem silo doc: hard stop explícito; não tenta LLM sem base.
            return self._hard_stop_result(
                query=query or user_message,
                reason="insufficient_context",
                mode=mode,
                discipline=effective_discipline,
                pin=pin,
                trace_retrieval=None,
            )

        # --- Retrieval bruto + política de decisão --------------------------

        candidates = self._search_engine.search_candidates(
            query,
            candidate_k=self._settings.retrieval_candidate_k,
            discipline_filter=effective_discipline,
        )
        decision = build_decision(
            query=query,
            candidates=candidates,
            mode=mode,
            min_score=self._settings.retrieval_min_score,
            min_score_margin=self._settings.retrieval_min_score_margin,
            min_coverage=self._settings.retrieval_min_coverage,
            min_coverage_weighted=self._settings.retrieval_min_coverage_weighted,
            min_terms=self._settings.retrieval_min_terms,
            top_k=self._settings.retrieval_top_k,
            max_per_source=self._settings.retrieval_max_chunks_per_source,
        )
        if decision.allow_generation:
            selected = [
                {
                    "source": c.source,
                    "text": c.text,
                    "score": c.raw_score,
                    "normalized_score": c.normalized_score,
                }
                for c in decision.selected_candidates
            ]
            ctx = "\n\n---\n\n".join(
                f"[Fonte: {s['source']} | Score: {s['normalized_score']:.2f}]\n{s['text']}"
                for s in selected
            )
            system_content = f"{sp}\n\n{_STRICT_GROUNDING_INSTRUCTION}{ctx}"

            if effective_discipline is not None:
                label = _trace_label_for_discipline(effective_discipline)
            elif force_rag:
                label = _global_scope_label(self._settings)
            else:
                label = _global_scope_label(self._settings)

            trace_sources = [s["source"] for s in selected]
            scope_key = self._scope_key_for_hit(
                force_rag, discipline_from_command, effective_discipline
            )
            self._save_pin(
                session_id,
                scope_key,
                [{"source": s["source"], "text": s["text"]} for s in selected],
                trace_sources,
            )

            trace = ContextTrace(
                label=label,
                sources=_dedupe_sources(trace_sources),
                pinned_active=self._pin_active(session_id),
                pinned_display=self._pin_display(session_id),
                mode=mode,
                decision="answer",
                reason=decision.reason,
                confidence=decision.confidence,
                retrieval_trace=decision.trace,
            )
            log_event(
                log,
                logging.INFO,
                ACL_MOD_CONTEXT,
                "context_prompt_ready",
                "mensagens montadas com chunks selecionados",
                metadata={
                    "selected_chunk_count": len(selected),
                    "sources": list(trace.sources),
                    "reason": decision.reason,
                    "confidence": decision.confidence,
                },
            )
            return BuildMessagesResult(
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": query},
                ],
                trace=trace,
                decision=decision,
            )

        # --- Hard stop ------------------------------------------------------
        # Pin NÃO ressuscita contexto: no modo strict, se a decisão atual
        # bloqueou, pin só serve como histórico de UI (mostrar o badge).
        return self._hard_stop_result(
            query=query or user_message,
            reason=decision.reason,
            mode=mode,
            discipline=effective_discipline,
            pin=pin,
            trace_retrieval=decision.trace,
            decision=decision,
        )

    # --- Helpers internos ---------------------------------------------------

    def _pin_active(self, session_id: str | None) -> bool:
        if not (self._pinned_store and session_id):
            return False
        return bool(self._pinned_store.get(session_id))

    def _pin_display(self, session_id: str | None) -> str | None:
        if not (self._pinned_store and session_id):
            return None
        p = self._pinned_store.get(session_id)
        return p.display_name if p else None

    def _save_pin(
        self,
        session_id: str | None,
        scope_key: str,
        chunk_dicts: list[dict[str, str]],
        sources_for_display: list[str],
    ) -> None:
        store = self._pinned_store
        if not (store and session_id):
            return
        trimmed = _trim_pin_chunks(chunk_dicts, self._settings.pinned_max_chars)
        if not trimmed:
            return
        disp = _display_name_from_source(sources_for_display[0]) if sources_for_display else "material"
        store.set_pinned(
            session_id,
            scope_key,
            trimmed,
            disp,
            self._settings.pinned_max_turns,
        )

    def _scope_key_for_hit(
        self,
        force_rag: bool,
        discipline_from_command: str | None,
        effective_discipline: str | None,
    ) -> str:
        if force_rag and discipline_from_command is None:
            return "content"
        if discipline_from_command is not None:
            return f"discipline:{discipline_from_command}"
        if effective_discipline is not None:
            return f"discipline:{effective_discipline}"
        return "content"

    def _hard_stop_result(
        self,
        query: str,
        reason: str,
        mode: str,
        discipline: str | None,
        pin: PinnedContext | None,
        trace_retrieval: RetrievalTrace | None,
        decision: RetrievalDecision | None = None,
    ) -> BuildMessagesResult:
        message = hard_stop_message(reason)
        label = (
            _trace_label_for_discipline(discipline)
            if discipline
            else _global_scope_label(self._settings)
        )
        trace_sources: list[str] = []
        if trace_retrieval is not None:
            trace_sources = [s["source"] for s in trace_retrieval.selected_sources]
        trace = ContextTrace(
            label=label,
            sources=_dedupe_sources(trace_sources),
            pinned_active=bool(pin),
            pinned_display=pin.display_name if pin else None,
            mode=mode,
            decision="hard_stop",
            reason=reason,
            confidence="low",
            retrieval_trace=trace_retrieval,
        )
        # Passamos uma sentinela no último user message; o ChatProvider
        # detecta decision.is_hard_stop via BuildMessagesResult.decision
        # e entrega `hard_stop_message` direto, sem chamar LLM.
        return BuildMessagesResult(
            messages=[
                {"role": "system", "content": self._settings.system_prompt_geral},
                {"role": "user", "content": query or ""},
                {"role": "assistant", "content": message},
            ],
            trace=trace,
            decision=decision,
        )
