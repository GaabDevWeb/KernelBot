"""Montagem de mensagens (system + user) para o chat com RAG /doc /content e contexto fixado por sessão."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from core.config import Settings
from engine.pinned_store import PinnedContext, PinnedSessionStore
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


@dataclass(frozen=True)
class ContextTrace:
    """Metadados para UI: rótulo de contexto, fontes e estado do pin."""

    label: str
    sources: tuple[str, ...]
    pinned_active: bool = False
    pinned_display: str | None = None


@dataclass(frozen=True)
class BuildMessagesResult:
    messages: list[dict]
    trace: ContextTrace


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


def _hits_weak(hits: list[dict], weak_score: float) -> bool:
    if not hits:
        return True
    mx = max(float(h["score"]) for h in hits)
    return mx < weak_score


def _join_pin_chunks(chunks: list[dict[str, str]]) -> str:
    return "\n\n---\n\n".join(
        f"[Fonte: {c['source']}]\n{c['text']}" for c in chunks if c.get("text")
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

        log.info(
            f"💬 Mensagem [{len(user_message)} chars] | force_rag={force_rag} | "
            f"force_doc={force_doc} | discipline={effective_discipline!r} | "
            f"cmd_disc={discipline_from_command!r} | reset={did_reset} | "
            f"pin={'sim' if pin else 'não'} | "
            f"query='{query[:80]}{'...' if len(query) > 80 else ''}'"
        )

        trace_label = "Assistente geral"
        trace_sources: list[str] = []
        used_sticky = False
        system_content = sp

        def finalize_trace() -> BuildMessagesResult:
            final_pin = store.get(session_id) if store and session_id else None
            pd = final_pin.display_name if final_pin else None
            pa = bool(final_pin)
            trace = ContextTrace(
                label=trace_label,
                sources=_dedupe_sources(trace_sources),
                pinned_active=pa,
                pinned_display=pd,
            )
            return BuildMessagesResult(
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": query},
                ],
                trace=trace,
            )

        def apply_sticky(p: PinnedContext) -> None:
            nonlocal system_content, trace_label, trace_sources, used_sticky
            used_sticky = True
            body = _join_pin_chunks(p.chunks)
            intro = self._settings.sticky_instruction.format(name=p.display_name or "material fixado") + "\n\n"
            system_content = (
                f"{sp}\n\n{intro}"
                "Você possui acesso à seguinte base de conhecimento local (contexto fixado).\n\n"
                f"{body}"
            )
            trace_sources = [str(c["source"]) for c in p.chunks if c.get("source")]
            if p.scope_key == "doc":
                trace_label = "Documentação (doc) · fixado"
            elif p.scope_key == "content":
                trace_label = f"{_global_scope_label(self._settings)} · fixado"
            elif p.scope_key.startswith("discipline:"):
                d = p.scope_key.split(":", 1)[1]
                trace_label = f"{_trace_label_for_discipline(d)} · fixado"
            else:
                trace_label = "Contexto fixado"

        def save_pin(scope_key: str, chunk_dicts: list[dict[str, str]], sources_for_display: list[str]) -> None:
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

        if force_doc:
            doc_chunks = [c for c in self._search_engine.chunks if c.get("discipline") == "doc"]
            if doc_chunks:
                log.info(f"   ⚡ /doc — injetando {len(doc_chunks)} chunk(s)")
                ctx = "\n\n---\n\n".join(
                    f"[Fonte: {c['source']}]\n{c['text']}" for c in doc_chunks
                )
                system_content = (
                    f"{sp}\n\n"
                    "Você possui acesso à documentação do sistema. "
                    "Utilize-a como referência rígida para responder:\n\n"
                    f"{ctx}"
                )
                trace_label = "Documentação (doc)"
                trace_sources = [str(c["source"]) for c in doc_chunks]
                pin_chunks = [{"source": str(c["source"]), "text": str(c["text"])} for c in doc_chunks]
                save_pin("doc", pin_chunks, trace_sources)
            else:
                log.warning("   ⚠ /doc sem chunks no silo 'doc'")
                system_content = sp
                trace_label = "Assistente geral"
                if pin:
                    apply_sticky(pin)
            return finalize_trace()

        hits = self._search_engine.search(query, discipline_filter=effective_discipline)
        weak = _hits_weak(hits, self._settings.pinned_weak_score)

        if hits and not weak:
            for h in hits:
                log.info(
                    f"   🎯 BM25 hit → '{h['source']}' | score={h['score']:.3f} | "
                    f"chunk='{h['text'][:60].strip()}...'"
                )
            ctx = "\n\n---\n\n".join(
                f"[Fonte: {h['source']} | Score: {h['score']:.2f}]\n{h['text']}"
                for h in hits
            )
            system_content = (
                f"{sp}\n\n"
                "Você possui acesso à seguinte base de conhecimento local. "
                "Use-a como referência primária para responder:\n\n"
                f"{ctx}"
            )
            if effective_discipline is not None:
                trace_label = _trace_label_for_discipline(effective_discipline)
            else:
                trace_label = _global_scope_label(self._settings)
            trace_sources = [str(h["source"]) for h in hits]
            if force_rag and discipline_from_command is None:
                sk = "content"
            elif discipline_from_command is not None:
                sk = f"discipline:{discipline_from_command}"
            elif effective_discipline is not None:
                sk = f"discipline:{effective_discipline}"
            else:
                sk = "content"
            save_pin(
                sk,
                [{"source": str(h["source"]), "text": str(h["text"])} for h in hits],
                trace_sources,
            )
        elif pin and (not hits or weak):
            log.info("   📌 BM25 fraco ou vazio — usando contexto fixado da sessão")
            apply_sticky(pin)
        elif hits:
            for h in hits:
                log.info(
                    f"   🎯 BM25 (fraco) → '{h['source']}' | score={h['score']:.3f} | "
                    f"chunk='{h['text'][:60].strip()}...'"
                )
            ctx = "\n\n---\n\n".join(
                f"[Fonte: {h['source']} | Score: {h['score']:.2f}]\n{h['text']}"
                for h in hits
            )
            system_content = (
                f"{sp}\n\n"
                "Você possui acesso à seguinte base de conhecimento local. "
                "Use-a como referência primária para responder:\n\n"
                f"{ctx}"
            )
            if effective_discipline is not None:
                trace_label = _trace_label_for_discipline(effective_discipline)
            else:
                trace_label = _global_scope_label(self._settings)
            trace_sources = [str(h["source"]) for h in hits]
        elif force_rag:
            scope_chunks = self._search_engine.chunks_for_scope(effective_discipline)
            log.info(
                "   ⚡ /content (ou RAG forçado) sem hits — top-5 do escopo "
                f"({len(scope_chunks)} chunk(s) disponíveis))"
            )
            ctx = "\n\n---\n\n".join(
                f"[Fonte: {c['source']}]\n{c['text']}" for c in scope_chunks[:5]
            )
            system_content = (
                f"{sp}\n\n"
                "Você possui acesso à seguinte base de conhecimento local. "
                "Use-a como referência primária para responder:\n\n"
                f"{ctx}"
            )
            if effective_discipline is not None:
                trace_label = _trace_label_for_discipline(effective_discipline)
            else:
                trace_label = _global_scope_label(self._settings)
            trace_sources = [str(c["source"]) for c in scope_chunks[:5]]
            sk = (
                "content"
                if discipline_from_command is None
                else f"discipline:{discipline_from_command}"
            )
            save_pin(
                sk,
                [{"source": str(c["source"]), "text": str(c["text"])} for c in scope_chunks[:5]],
                trace_sources,
            )
        elif pin:
            log.info("   📌 Modo geral sem BM25 — usando contexto fixado")
            apply_sticky(pin)
        else:
            log.info("   🤖 Modo assistente geral (sem hits nem pin)")
            trace_label = "Assistente geral"
            trace_sources = []

        log.info(f"   🔑 System prompt ~{len(system_content)} chars | sticky={used_sticky}")
        return finalize_trace()
