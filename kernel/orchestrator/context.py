"""Montagem de mensagens (system + user) para o chat com RAG /doc /content.

Este módulo consome `kernel.rag.retrieval.build_decision` e monta o prompt
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

from urllib.parse import unquote

from kernel.config import Settings
from kernel.context.conversation_context import (
    MEDIA_ABSTENTION_BLOCK,
    THREAD_UNCLEAR_BLOCK,
    detect_social_conflict,
    needs_media_abstention,
    resolve_query_from_recent,
)
from kernel.context.builder import ContextBuilder, ContextLayers, SystemContextBlocks
from kernel.context.domain_router import DomainRouteResult, DomainRouter
from kernel.context.intent import detect_temporal_intent, is_calendar_priority_query
from kernel.context.router import ContextRouter
from kernel.context.types import ContextRoute, RagSkipReason, RouteSignals
from kernel.group.invocation import (
    derive_rag_query_from_recent,
    format_recent_context_block,
    parse_invocation_from_metadata,
    user_turn_content,
)
from kernel.disciplines.disciplines import command_prefixes, query_markers_by_discipline, trace_label_by_discipline
from kernel.knowledge.iss_links import format_source_header, format_source_label
from kernel.knowledge.lesson_catalog import CatalogMatchResult, LessonCatalog, LessonEntry, parse_db_source_key
from kernel.memory.group_memory import GroupMemoryStore, HistoricalSearchResult
from kernel.memory.group_profile import GroupProfile
from kernel.memory.pinned_store import PinnedContext, PinnedSessionStore
from kernel.rag.retrieval import (
    RetrievalCandidate,
    RetrievalDecision,
    RetrievalTrace,
    build_decision,
    extract_informative_terms,
    select_mode,
)
from kernel.rag.search import SearchEngine
from kernel.structured_log import ACL_MOD_CONTEXT, log_event

_CATALOG_RESCUE_REASONS: frozenset[str] = frozenset({"ambiguous_retrieval"})

log = logging.getLogger(f"kernelbots.{__name__}")

# Mais longo primeiro; exige espaço ou fim após o prefixo (evita `/pythonfoo`).
# SSOT: core/disciplines.json
_DISCIPLINE_COMMAND_PREFIXES: tuple[tuple[str, str], ...] = command_prefixes()

_TRACE_LABEL_BY_DISCIPLINE: dict[str, str] = trace_label_by_discipline()

_TOPIC_TO_SILO: dict[str, str] = {
    "java": "fundamentos-java",
    "csharp": "fundamentos-csharp",
    "python": "python",
    "sql": "sql-modelagem-relacional",
    "backend": "projeto-bloco-backend",
    "ia": "fluencia-ia",
}

_SOURCES_CAP = 20

_RESET_PREFIX_RE = re.compile(r"^/(?:reset|limpar)\s*", re.IGNORECASE)

_CATALOG_LESSON_BOOST_FACTOR = 1.35


def _expand_query_with_discipline_markers(
    query: str,
    retrieval_scopes: tuple[str, ...],
    *,
    max_markers: int = 3,
) -> str:
    """Enriquece query BM25 com markers do domínio (não altera mensagem ao LLM)."""
    q_lower = query.lower()
    if any(h in q_lower for h in ("c#", "java", "python", " sql", "sql ", "mysql")):
        return query
    markers_map = query_markers_by_discipline()
    extra: list[str] = []
    for scope in retrieval_scopes:
        for marker in markers_map.get(scope, ()):
            m = marker.lower()
            if m not in q_lower and m not in extra:
                extra.append(marker)
            if len(extra) >= max_markers:
                break
        if len(extra) >= max_markers:
            break
    if not extra:
        return query
    return f"{query} {' '.join(extra)}"


def _boost_candidates_for_catalog_lesson(
    candidates: list[RetrievalCandidate],
    lesson_key: str,
    *,
    boost_factor: float = _CATALOG_LESSON_BOOST_FACTOR,
) -> list[RetrievalCandidate]:
    """Promove chunks da aula identificada pelo catálogo lexical."""
    boosted: list[RetrievalCandidate] = []
    for cand in candidates:
        key = parse_db_source_key(cand.source)
        if key == lesson_key:
            boosted.append(
                RetrievalCandidate(
                    source=cand.source,
                    chunk_id=cand.chunk_id,
                    text=cand.text,
                    discipline=cand.discipline,
                    raw_score=cand.raw_score * boost_factor,
                    normalized_score=min(1.0, cand.normalized_score * boost_factor),
                    matched_terms=cand.matched_terms,
                )
            )
        else:
            boosted.append(cand)
    boosted.sort(key=lambda c: c.raw_score, reverse=True)
    return boosted


# --- Mensagens UX padronizadas (Fase 1/3) -----------------------------------

_HARD_STOP_MESSAGES: dict[str, str] = {
    "insufficient_context": (
        "Não achei informação suficiente no material para responder com segurança.\n\n"
        "Tenta ser mais específico: tecnologia, contexto ou o que você quer fazer."
    ),
    "context_misaligned": (
        "Achei trechos na base, mas nada que cubra bem a pergunta.\n\n"
        "Reformula com termos mais específicos."
    ),
    "underspecified_query": (
        "A pergunta está vaga demais para eu responder com segurança.\n\n"
        "Formato útil: [tecnologia] + [problema] + [contexto].\n\n"
        "Exemplos:\n"
        "- SQL + performance + query lenta\n"
        "- Docker + erro + build falhando\n"
        "- API + timeout + chamada de autenticação"
    ),
    "vague_but_high_risk": (
        "Isso pode significar coisas diferentes e eu não tenho contexto para escolher uma.\n\n"
        "Reformula com: [tecnologia] + [problema] + [contexto]."
    ),
    "ambiguous_retrieval": (
        "Achei conteúdos parecidos e não consegui distinguir qual responde à pergunta.\n\n"
        "Adiciona detalhe: módulo, comando ou tecnologia."
    ),
    "low_confidence": (
        "Tem material parecido, mas a confiança ficou baixa — no modo estrito prefiro não chutar.\n\n"
        "Reformula com mais detalhe ou usa um comando de escopo (`/doc`, `/python`, etc.)."
    ),
    "post_generation_misalignment": (
        "Montei uma resposta, mas a checagem final indicou que saiu do escopo das fontes.\n\n"
        "Reformula com termos mais próximos do material ou tenta de novo."
    ),
    "index_gap": (
        "O tópico está no catálogo, mas o conteúdo ainda não está no índice de busca.\n\n"
        "Tenta de novo depois do `/reload` ou avisa o responsável."
    ),
    "provider_error": (
        "Deu problema ao contatar o modelo.\n\n"
        "Tenta de novo em alguns instantes. Se persistir, avisa o responsável."
    ),
}


def hard_stop_message(reason: str) -> str:
    return _HARD_STOP_MESSAGES.get(
        reason,
        "Não consegui responder com segurança agora. Reformula e tenta de novo.",
    )


_MAX_HISTORY_ITEMS_RAW = 40
_MAX_HISTORY_CONTENT_LEN = 8192
_VALID_HISTORY_ROLES = frozenset({"user", "assistant"})


class ConversationHistoryError(ValueError):
    """History inválido no body do POST /chat."""


def _normalize_conversation_history(raw: object) -> list[dict[str, str]]:
    """Valida e normaliza history do cliente (sem role system)."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ConversationHistoryError("Campo 'history' deve ser uma lista.")
    if len(raw) > _MAX_HISTORY_ITEMS_RAW:
        raise ConversationHistoryError(
            f"Campo 'history' excede o máximo de {_MAX_HISTORY_ITEMS_RAW} itens."
        )
    out: list[dict[str, str]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ConversationHistoryError(f"history[{i}] deve ser um objeto.")
        role = item.get("role")
        if role == "system":
            raise ConversationHistoryError(
                "role 'system' não é permitido em history (reservado ao servidor)."
            )
        if role not in _VALID_HISTORY_ROLES:
            raise ConversationHistoryError(
                f"history[{i}].role deve ser 'user' ou 'assistant'."
            )
        content = item.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ConversationHistoryError(f"history[{i}].content ausente ou vazio.")
        text = content.strip()
        if len(text) > _MAX_HISTORY_CONTENT_LEN:
            text = text[:_MAX_HISTORY_CONTENT_LEN]
        out.append({"role": str(role), "content": text})
    return out


def _truncate_conversation_history(
    history: list[dict[str, str]],
    *,
    max_turns: int,
    max_chars: int,
) -> list[dict[str, str]]:
    """Mantém os turnos mais recentes dentro dos limites de mensagens e caracteres."""
    if not history or max_turns <= 0:
        return []
    trimmed = history[-max_turns:]
    kept_rev: list[dict[str, str]] = []
    total = 0
    for msg in reversed(trimmed):
        content = msg["content"]
        if total + len(content) > max_chars and kept_rev:
            break
        if total + len(content) > max_chars:
            kept_rev.append(
                {"role": msg["role"], "content": content[:max_chars]}
            )
            break
        total += len(content)
        kept_rev.append(msg)
    return list(reversed(kept_rev))


def _merge_messages_with_history(
    system_content: str,
    history: list[dict[str, str]],
    current_user: str,
) -> list[dict[str, str]]:
    """system → history truncado → user atual."""
    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
    messages.extend(history)
    messages.append({"role": "user", "content": current_user})
    return messages


@dataclass(frozen=True)
class ContextTrace:
    """Metadados para UI: rótulo de contexto, fontes, pin, decisão e confiança."""

    label: str
    sources: tuple[str, ...]
    source_details: tuple[dict, ...] = ()
    pinned_active: bool = False
    pinned_display: str | None = None
    pin_chunks_used: bool = False
    pinned_scope_key: str | None = None
    scope_hint: str | None = None
    suggested_scope_command: str | None = None
    sources_note: str | None = None
    mode: str = "strict"
    decision: str = "answer"
    reason: str = "ok"
    confidence: str = "high"
    retrieval_trace: RetrievalTrace | None = None
    catalog_match: bool = False
    hard_stop_payload: dict | None = None
    # Camadas de contexto (identity/institucional/temporal/calendar) —
    # observabilidade; defaults preservam construções existentes.
    temporal_context: dict | None = None
    calendar_context: dict | None = None
    temporal_intent: str | None = None
    rag_skipped: bool = False
    institutional_files: tuple[str, ...] = ()
    identity_active: bool = False
    # ContextRouter (ACL_CONTEXT_ROUTER) — campos opcionais; ausentes = legado.
    router_enabled: bool = False
    context_profile: str | None = None
    rag_skip_reason: str | None = None
    include_institutional: bool | None = None
    include_calendar: bool | None = None
    transcript_turns_requested: int | None = None
    transcript_turns_used: int | None = None
    router_reasons: tuple[str, ...] = ()
    # Memória Histórica e Social de Grupos
    group_memory_used: bool = False
    group_memory_hits: tuple[dict, ...] = ()
    group_profile_active: bool = False
    group_profile_topics: tuple[str, ...] = ()
    invocation_type: str | None = None
    contextual_invocation: bool = False
    recent_context_count: int = 0
    no_useful_context: bool = False
    # Domain Router (ACL_DOMAIN_ROUTER) — scoped retrieval.
    domain_router_enabled: bool = False
    domain_candidates: tuple[dict, ...] = ()
    selected_domain: str | None = None
    selected_domains: tuple[str, ...] = ()
    domain_confidence: float | None = None
    domain_retrieval_scope: tuple[str, ...] = ()
    domain_fallback: bool = False
    domain_multi: bool = False
    domain_router_reason: str | None = None
    domain_router_latency_ms: float | None = None
    behavior_flags: tuple[str, ...] = ()
    conversation_resolution_k: int = 0
    dominant_conversation_topic: str | None = None
    conversation_ambiguous: bool = False


@dataclass(frozen=True)
class BuildMessagesResult:
    messages: list[dict]
    trace: ContextTrace
    decision: RetrievalDecision | None = None
    # Candidatos BM25 considerados (observabilidade; não altera o prompt).
    candidates_considered: tuple = ()
    effective_discipline: str | None = None


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


def _dominant_discipline_from_chunks(chunks: list[dict[str, str]]) -> str | None:
    """Disciplina mais frequente nas fontes do pin (ex.: scope_key=content)."""
    counts: dict[str, int] = {}
    for c in chunks:
        src = (c.get("source") or "").lower()
        m = re.search(r"db:([^/]+)/", src)
        if m:
            disc = m.group(1)
            counts[disc] = counts.get(disc, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def _effective_pin_discipline(pin: PinnedContext) -> str | None:
    explicit = _discipline_from_pin_scope(pin)
    if explicit:
        return explicit
    return _dominant_discipline_from_chunks(pin.chunks)


_FOLLOW_UP_PREFIX_RE = re.compile(
    r"^(e\s+)?(o\s+que\s+é|o\s+que\s+e|e\s+o|e\s+a|e\s+isso|também|tambem)\b",
    re.IGNORECASE,
)

_FOLLOW_UP_TOPIC_MARKERS = (
    "f-string",
    "fstring",
    "elif",
    "jupyter",
    "variável",
    "variavel",
    "loop",
    "enumerate",
    "nameerror",
    "snake_case",
)


def _is_short_follow_up_query(query: str, informative_count: int, *, min_terms: int = 2) -> bool:
    if informative_count >= min_terms:
        return False
    q = query.strip()
    if not q:
        return False
    if _FOLLOW_UP_PREFIX_RE.match(q) and len(q) <= 80:
        return True
    ql = q.lower()
    if len(q.split()) <= 5 and any(m in ql for m in _FOLLOW_UP_TOPIC_MARKERS):
        return True
    return False


def _relax_weak_reason_for_pinned_follow_up(
    reason: str,
    query: str,
    pin: PinnedContext | None,
    pin_chunks_used: bool,
) -> str:
    if reason != "underspecified_query" or not pin or not pin_chunks_used:
        return reason
    informative = extract_informative_terms(query)
    if _is_short_follow_up_query(query, len(informative)):
        return "ok"
    return reason


_QUERY_MARKERS_BY_DISCIPLINE: dict[str, tuple[str, ...]] = query_markers_by_discipline()

_PIN_POISONING_RE = re.compile(
    r"(ignore\s+(todas\s+as\s+)?regras|ignore\s+suas\s+instru|developer\s+mode|"
    r"você\s+agora\s+é\s+dan\b|chatgpt\s+with|"
    r"malware|senha\s+do\s+banco|gabarito\s+do\s+at|"
    r"api\s+key\s+real|\[INJECT\]|reveal\s+secrets|"
    r"omega\s+\(|uncensored\s+creativity)",
    re.IGNORECASE,
)


def _infer_query_discipline_from_text(query: str) -> str | None:
    """Heurística leve: disciplina provável da pergunta (sem LLM)."""
    q = query.lower()
    scores: dict[str, int] = {
        disc: sum(1 for m in markers if m in q)
        for disc, markers in _QUERY_MARKERS_BY_DISCIPLINE.items()
    }
    best_score = max(scores.values()) if scores else 0
    if best_score < 1:
        return None
    winners = [disc for disc, n in scores.items() if n == best_score]
    if len(winners) != 1:
        return None
    return winners[0]


def _pin_inherited_discipline_filter(
    query: str,
    pin: PinnedContext | None,
) -> str | None:
    """Disciplina herdada do pin para filtro BM25; None se domínio mudou."""
    if pin is None:
        return None
    explicit = _discipline_from_pin_scope(pin)
    if not explicit:
        return None
    informative = extract_informative_terms(query)
    if _is_short_follow_up_query(query, len(informative)):
        return explicit
    inferred = _infer_query_discipline_from_text(query)
    if inferred and inferred != explicit:
        return None
    return explicit


def _should_skip_pin_update(
    query: str, *, did_reset: bool, doc_rag_active: bool = False
) -> bool:
    """Evita fixar pin após reset, confirmação de reset ou turnos adversariais."""
    if doc_rag_active:
        return True
    if did_reset:
        return True
    if "contexto fixado foi removido" in query.lower():
        return True
    return bool(_PIN_POISONING_RE.search(query))


def _discipline_display_name(disc_id: str) -> str:
    return _TRACE_LABEL_BY_DISCIPLINE.get(disc_id, disc_id.replace("-", " ").title())


def _retrieval_adds_sources_beyond_pin(
    pin: PinnedContext | None,
    retrieval_chunks: list[dict[str, str | float]],
) -> bool:
    """True quando a busca deste turno traz fontes fora do pin do turno anterior."""
    if not pin or not pin.chunks:
        return False
    pin_sources = {
        str(c.get("source") or "")
        for c in pin.chunks
        if c.get("source")
    }
    for s in retrieval_chunks:
        src = str(s.get("source") or "")
        if src and src not in pin_sources:
            return True
    return False


def _build_scope_ui_hints(
    pin: PinnedContext | None,
    query: str,
    discipline_from_command: str | None,
    pin_chunks_used: bool,
    *,
    sources_mix_this_turn: bool = False,
) -> tuple[str | None, str | None, str | None, str | None]:
    """(pinned_scope_key, scope_hint, suggested_scope_command, sources_note)."""
    if not pin:
        return None, None, None, None

    pinned_scope_key = pin.scope_key
    sources_note: str | None = None
    if sources_mix_this_turn:
        sources_note = (
            "Rodapé deste turno combina fontes do contexto anterior com a busca atual — "
            "use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar."
        )

    pin_disc = _effective_pin_discipline(pin)
    inferred = _infer_query_discipline_from_text(query)
    scope_hint: str | None = None
    suggested: str | None = None

    if discipline_from_command and pin_disc and discipline_from_command != pin_disc:
        suggested = f"/{discipline_from_command}"
        scope_hint = (
            f"Tema fixado em «{pin.display_name}» ({_discipline_display_name(pin_disc)}), "
            f"mas você usou {suggested}. Use /reset para limpar o pin ou continue em {suggested}."
        )
        return pinned_scope_key, scope_hint, suggested, sources_note

    if pin_chunks_used and pin_disc and inferred and inferred != pin_disc:
        suggested = f"/{inferred}"
        scope_hint = (
            f"Tema fixado em «{pin.display_name}». A pergunta parece ser de "
            f"{_discipline_display_name(inferred)} — use {suggested} no início ou "
            "/reset para limpar o contexto fixado."
        )

    return pinned_scope_key, scope_hint, suggested, sources_note


def _display_name_from_source(source: str) -> str:
    stem = Path(source.replace("\\", "/")).stem
    return stem.replace("-", " ").strip() or source


_LESSON_ORDER_RE = re.compile(r"__(\d+)__")


def _lesson_sequence_label(slug: str) -> str | None:
    m = _LESSON_ORDER_RE.search(slug or "")
    if not m:
        return None
    return f"Aula {int(m.group(1))}"


def _excerpt_for_ui(text: str, *, max_len: int = 220) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return ""
    if len(cleaned) <= max_len:
        return cleaned
    cut = cleaned[:max_len].rsplit(" ", 1)[0]
    return (cut or cleaned[:max_len]).strip() + "…"


def _build_source_details_for_ui(
    merged_chunks: list[dict[str, str]],
    lesson_catalog: LessonCatalog | None,
    iss_public_base: str = "",
) -> tuple[dict, ...]:
    """Metadados ricos para cards de fonte na UI (título, trecho, disciplina)."""
    out: list[dict] = []
    seen: set[str] = set()
    for chunk in merged_chunks:
        src = str(chunk.get("source") or "").strip()
        if not src or src in seen:
            continue
        seen.add(src)
        disc = ""
        slug = ""
        if src.startswith("db:"):
            rest = src[3:]
            parts = [p for p in rest.split("/") if p]
            if len(parts) >= 2:
                disc, slug = parts[0], parts[1].split("/", 1)[0]
            elif len(parts) == 1:
                slug = parts[0]

        entry = lesson_catalog.entry_for_source(src) if lesson_catalog else None
        lesson_title = (
            (entry.title or entry.name).strip()
            if entry
            else _display_name_from_source(src)
        )
        chunk_excerpt = _excerpt_for_ui(chunk.get("text") or "")
        catalog_excerpt = (entry.excerpt or "").strip() if entry else ""
        excerpt = chunk_excerpt or _excerpt_for_ui(catalog_excerpt, max_len=220)

        module = _lesson_sequence_label(slug or (entry.slug if entry else ""))
        disc_label = _discipline_display_name(disc) if disc else "Material"
        public_url = format_source_label(src, iss_public_base)
        if not public_url.startswith("http"):
            public_url = ""

        out.append(
            {
                "source": src,
                "discipline": disc,
                "discipline_label": disc_label,
                "slug": slug or (entry.slug if entry else ""),
                "lesson_title": lesson_title,
                "module": module,
                "excerpt": excerpt,
                "public_url": public_url,
            }
        )
    return tuple(out)


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


def _join_chunks_for_prompt(selected: list[dict[str, str]], settings: Settings) -> str:
    return "\n\n---\n\n".join(
        f"{format_source_header(c['source'], settings.iss_public_lesson_base)}\n{c['text']}"
        for c in selected
        if c.get("text")
    )


def _merge_pin_and_retrieval_chunks(
    pin: PinnedContext | None,
    retrieval_chunks: list[dict[str, str | float]],
    max_chars: int,
) -> list[dict[str, str]]:
    """Pin primeiro, depois retrieval; dedupe por source; respeita max_chars."""
    merged: list[dict[str, str]] = []
    seen_sources: set[str] = set()

    if pin and pin.chunks:
        for c in pin.chunks:
            src = str(c.get("source") or "")
            if src and src not in seen_sources:
                seen_sources.add(src)
                merged.append({"source": src, "text": str(c.get("text") or "")})

    for s in retrieval_chunks:
        src = str(s.get("source") or "")
        text = str(s.get("text") or "")
        if not src or not text or src in seen_sources:
            continue
        seen_sources.add(src)
        merged.append({"source": src, "text": text})

    return _trim_pin_chunks(merged, max_chars)


_WEAK_GROUNDING_REASONS = frozenset({
    "insufficient_context",
    "context_misaligned",
    "underspecified_query",
    "low_confidence",
    "vague_but_high_risk",
})


def _select_grounding(decision: RetrievalDecision, settings: Settings) -> str:
    """Escolhe o contrato de grounding conforme política, decisão e flags de produto."""
    if decision.reason == "ambiguous_retrieval" and settings.disambiguation_enabled:
        return settings.grounding_disambiguation
    if settings.grounding_policy == "strict":
        return settings.grounding_strict
    if settings.grounding_policy == "anchored":
        return settings.grounding_anchored
    # hybrid
    if decision.reason == "ok" and decision.selected_candidates:
        return settings.grounding_anchored
    if decision.reason in _WEAK_GROUNDING_REASONS:
        if decision.selected_candidates:
            return settings.grounding_anchored
        return settings.grounding_permissive
    return settings.grounding_anchored


def _format_chunks_for_prompt(
    selected: list[dict[str, str | float]],
    decision: RetrievalDecision,
    settings: Settings,
) -> str:
    """Formata trechos RAG; numera fontes em modo desambiguação."""
    if not selected:
        return ""
    use_numbered = (
        decision.reason == "ambiguous_retrieval" and settings.disambiguation_enabled
    )
    parts: list[str] = []
    for i, s in enumerate(selected, start=1):
        text = s.get("text") or ""
        if not text:
            continue
        src = s.get("source") or ""
        score = s.get("normalized_score")
        score_f = float(score) if score is not None else None
        if use_numbered:
            header = format_source_header(
                str(src),
                settings.iss_public_lesson_base,
                index=i,
                score=score_f,
            )
        else:
            header = format_source_header(
                str(src),
                settings.iss_public_lesson_base,
                score=score_f,
            )
        parts.append(f"{header}\n{text}")
    return "\n\n---\n\n".join(parts)


def _sticky_block_for_pin(settings: Settings, pin: PinnedContext | None) -> str:
    if not pin or not pin.display_name:
        return ""
    return settings.sticky_instruction.format(name=pin.display_name)


def _lesson_dict_from_entry(lesson: LessonEntry) -> dict[str, str]:
    return {
        "title": lesson.title,
        "discipline": lesson.discipline,
        "slug": lesson.slug,
    }


def _catalog_suggested_candidates(catalog_result: CatalogMatchResult) -> list[dict[str, str]]:
    return [_lesson_dict_from_entry(m.lesson) for m in catalog_result.matches[:3]]


def _enrich_hard_stop_with_catalog(
    reason: str,
    catalog_result: CatalogMatchResult | None,
) -> str:
    message = hard_stop_message(reason)
    if catalog_result is None or not catalog_result.matches:
        return message
    if reason not in _CATALOG_RESCUE_REASONS:
        return message
    lines = [
        message,
        "",
        "Com base no catálogo de aulas, estas opções podem corresponder melhor:",
    ]
    for m in catalog_result.matches[:3]:
        les = m.lesson
        lines.append(f"- **{les.name}** (`{les.discipline}/{les.slug}`)")
    lines.append(
        "\nReformule citando módulo, comando ou tecnologia para desempatar, "
        "ou use um prefixo de escopo (ex.: `/python`, `/visualizacao-sql`)."
    )
    return "\n".join(lines)


class ContextManager:
    def __init__(
        self,
        settings: Settings,
        search_engine: SearchEngine,
        pinned_store: PinnedSessionStore | None = None,
        lesson_catalog: LessonCatalog | None = None,
        indexed_lesson_keys: frozenset[str] | None = None,
        context_builder: ContextBuilder | None = None,
        group_memory_store: GroupMemoryStore | None = None,
    ) -> None:
        self._settings = settings
        self._search_engine = search_engine
        self._pinned_store = pinned_store
        self._lesson_catalog = lesson_catalog
        self._indexed_lesson_keys = indexed_lesson_keys or frozenset()
        # Camadas novas são opt-in: sem builder, o comportamento é o anterior.
        self._context_builder = context_builder
        self._context_router = ContextRouter()
        indexed = getattr(search_engine, "discipline_ids", frozenset())
        self._domain_router = DomainRouter(
            indexed_disciplines=indexed if isinstance(indexed, frozenset) else frozenset(indexed),
        )
        self._group_memory_store = group_memory_store

    @property
    def settings(self) -> Settings:
        return self._settings

    def refresh_indexed_lesson_keys(self, keys: frozenset[str]) -> None:
        self._indexed_lesson_keys = keys

    def _catalog_match(self, query: str) -> CatalogMatchResult | None:
        if not self._lesson_catalog or not query.strip():
            return None
        return self._lesson_catalog.match(query)

    def _try_catalog_rescue(
        self,
        query: str,
        decision: RetrievalDecision,
        mode: str,
        catalog_result: CatalogMatchResult,
    ) -> RetrievalDecision:
        if decision.reason not in _CATALOG_RESCUE_REASONS:
            return decision
        if not self._lesson_catalog or not self._lesson_catalog.is_confident(catalog_result):
            return decision

        lesson = self._lesson_catalog.top_lesson(catalog_result)
        if lesson is None:
            return decision

        narrowed_discipline = self._sanitize_discipline(lesson.discipline)
        candidates = self._search_engine.search_candidates(
            query,
            candidate_k=self._settings.retrieval_candidate_k,
            discipline_filter=narrowed_discipline,
        )
        candidates = self._lesson_catalog.filter_candidates_to_lesson(candidates, lesson)
        if not candidates:
            log.debug("catalog_rescue_aborted_empty_candidates")
            return decision

        rescued = build_decision(
            query=query,
            candidates=candidates,
            mode=mode,  # type: ignore[arg-type]
            min_score=self._settings.retrieval_min_score,
            min_score_margin=self._settings.retrieval_min_score_margin,
            min_coverage=self._settings.retrieval_min_coverage,
            min_coverage_weighted=self._settings.retrieval_min_coverage_weighted,
            min_terms=self._settings.retrieval_min_terms,
            top_k=self._settings.retrieval_top_k,
            max_per_source=self._settings.retrieval_max_chunks_per_source,
            acl_retrieval_mode=self._settings.retrieval_mode,
            disambiguation_enabled=self._settings.disambiguation_enabled,
        )
        if not rescued.selected_candidates:
            return decision

        log_event(
            log,
            logging.INFO,
            ACL_MOD_CONTEXT,
            "catalog_rescue_ok",
            "BM25 restrito pela aula do catalogo",
            metadata={
                "original_reason": decision.reason,
                "lesson_slug": lesson.slug,
                "lesson_discipline": lesson.discipline,
                "catalog_top_score": catalog_result.top_score,
            },
        )
        debug = dict(rescued.trace.debug)
        debug["catalog_rescue"] = {
            "lesson_id": lesson.lesson_id,
            "slug": lesson.slug,
            "discipline": lesson.discipline,
        }
        return RetrievalDecision(
            allow_generation=rescued.allow_generation,
            reason=rescued.reason,
            confidence=rescued.confidence,
            selected_candidates=rescued.selected_candidates,
            trace=RetrievalTrace(
                query=rescued.trace.query,
                normalized_query=rescued.trace.normalized_query,
                informative_terms=rescued.trace.informative_terms,
                mode=rescued.trace.mode,
                retrieval_mode="bm25_lexical+catalog_rescue",
                top_score=rescued.trace.top_score,
                second_score=rescued.trace.second_score,
                score_margin=rescued.trace.score_margin,
                coverage=rescued.trace.coverage,
                selected_sources=rescued.trace.selected_sources,
                decision=rescued.trace.decision,
                reason=rescued.trace.reason,
                llm_called=rescued.trace.llm_called,
                tokens_used=rescued.trace.tokens_used,
                debug=debug,
            ),
        )

    def _sanitize_discipline(self, raw: str | None) -> str | None:
        return self._search_engine.normalize_discipline(raw)

    def build_messages(
        self,
        user_message: str,
        discipline_filter: str | None = None,
        session_id: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        *,
        top_k: int | None = None,
        request_metadata: dict | None = None,
        channel_id: str | None = None,
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

        parsed_invocation = parse_invocation_from_metadata(
            request_metadata,
            channel_id=channel_id or "",
            message=user_message,
        )
        recent_context_block = ""
        if parsed_invocation.is_contextual:
            recent_context_block = format_recent_context_block(
                parsed_invocation.recent_context,
                max_messages=self._settings.chat_history_max_turns,
                max_chars=self._settings.chat_history_max_chars,
            )
            if parsed_invocation.quoted_context:
                recent_context_block = (
                    f"{recent_context_block}\n\nMensagem citada:\n{parsed_invocation.quoted_context}"
                    if recent_context_block
                    else f"Mensagem citada:\n{parsed_invocation.quoted_context}"
                )
            if not query.strip():
                query = derive_rag_query_from_recent(parsed_invocation.recent_context)

        behavior_advisory = ""
        conversation_resolution_k = 0
        dominant_conversation_topic: str | None = None
        conversation_ambiguous = False
        behavior_flags: list[str] = []

        if parsed_invocation.recent_context:
            resolution = resolve_query_from_recent(
                query if query.strip() else user_message,
                parsed_invocation.recent_context,
                k=4,
            )
            conversation_resolution_k = resolution.resolution_k
            dominant_conversation_topic = resolution.dominant_topic
            conversation_ambiguous = resolution.ambiguous_unresolved
            if resolution.was_resolved:
                query = resolution.resolved
                behavior_flags.append("coreference_resolved")
            elif resolution.ambiguous_unresolved:
                behavior_advisory = THREAD_UNCLEAR_BLOCK
                behavior_flags.append("ambiguous_unresolved")
            elif not query.strip():
                query = derive_rag_query_from_recent(parsed_invocation.recent_context)

        conflict_hint = detect_social_conflict(parsed_invocation.recent_context)
        if conflict_hint:
            behavior_advisory = (
                f"{behavior_advisory}\n\n{conflict_hint.prompt_note}".strip()
                if behavior_advisory
                else conflict_hint.prompt_note
            )
            behavior_flags.append("social_conflict_detected")

        if needs_media_abstention(
            user_message,
            parsed_invocation.recent_context,
            quoted_context=parsed_invocation.quoted_context,
        ):
            behavior_advisory = (
                f"{behavior_advisory}\n\n{MEDIA_ABSTENTION_BLOCK}".strip()
                if behavior_advisory
                else MEDIA_ABSTENTION_BLOCK
            )
            behavior_flags.append("media_abstention")

        if behavior_flags:
            log_event(
                log,
                logging.INFO,
                ACL_MOD_CONTEXT,
                "behavior_gate",
                "sinais P0 conversacionais",
                metadata={
                    "flags": list(behavior_flags),
                    "resolution_k": conversation_resolution_k,
                    "dominant_topic": dominant_conversation_topic,
                    "ambiguous": conversation_ambiguous,
                },
            )

        llm_user_content = user_turn_content(user_message, parsed_invocation)
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
            effective_discipline = self._sanitize_discipline(
                _pin_inherited_discipline_filter(query, pin)
            )
        else:
            effective_discipline = None

        if (
            effective_discipline is None
            and dominant_conversation_topic
            and dominant_conversation_topic in _TOPIC_TO_SILO
            and not force_doc
        ):
            hinted = self._sanitize_discipline(_TOPIC_TO_SILO[dominant_conversation_topic])
            if hinted is not None:
                effective_discipline = hinted
                behavior_flags.append("topic_silo_hint")

        doc_rag_active = False
        if force_doc:
            has_doc_silo = any(
                c.get("discipline") == "doc" for c in self._search_engine.chunks
            )
            if has_doc_silo:
                doc_rag_active = True
                effective_discipline = self._sanitize_discipline("doc")

        skip_pin_update = _should_skip_pin_update(
            query, did_reset=did_reset, doc_rag_active=doc_rag_active
        )

        history_in = conversation_history or []
        router_enabled = bool(
            getattr(self._settings, "context_router_enabled", False)
        )
        route: ContextRoute | None = None
        rag_skip_reason: str | None = None
        filter_low_confidence_rag = False

        if router_enabled and self._context_builder is not None:
            temporal_intent = detect_temporal_intent(query or llm_user_content)
            route = self._context_router.route(
                query,
                signals=RouteSignals(
                    force_doc=force_doc,
                    force_rag=force_rag,
                    discipline_from_command=discipline_from_command,
                    history_turns=len(history_in),
                    temporal_intent=temporal_intent,
                    chat_history_max_turns=self._settings.chat_history_max_turns,
                    contextual_invocation=parsed_invocation.is_contextual
                    and not user_message.strip(),
                    no_useful_context=parsed_invocation.no_useful_context,
                ),
            )
            history_max_turns = min(
                self._settings.chat_history_max_turns,
                max(0, int(route.transcript_max_turns)),
            )
            rag_skipped = bool(route.rag_skipped)
            rag_skip_reason = route.rag_skip_reason.value
            filter_low_confidence_rag = bool(route.filter_low_confidence_rag)
            layers = self._context_builder.build_layers(route=route)
        else:
            layers = (
                self._context_builder.build_layers()
                if self._context_builder is not None
                else ContextLayers()
            )
            temporal_intent = (
                detect_temporal_intent(query)
                if layers.temporal is not None
                else None
            )
            calendar_priority = is_calendar_priority_query(query)
            history_max_turns = self._settings.chat_history_max_turns
            # Legado: RAG dispensável em time_fact puro ou pergunta de agenda.
            rag_skipped = bool(
                (
                    temporal_intent is not None
                    and temporal_intent.kind == "time_fact"
                    and not force_doc
                    and not force_rag
                    and discipline_from_command is None
                )
                or (
                    calendar_priority
                    and not force_doc
                    and not force_rag
                    and discipline_from_command is None
                )
            )
            if rag_skipped:
                rag_skip_reason = (
                    RagSkipReason.TEMPORAL_FACT.value
                    if temporal_intent is not None and temporal_intent.kind == "time_fact"
                    else RagSkipReason.CALENDAR_ONLY.value
                )
                filter_low_confidence_rag = calendar_priority

        history_truncated = _truncate_conversation_history(
            history_in,
            max_turns=history_max_turns,
            max_chars=self._settings.chat_history_max_chars,
        )
        history_used_chars = sum(len(m["content"]) for m in history_truncated)

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
                "history_turns_in": len(history_in),
                "history_turns_used": len(history_truncated),
                "history_chars_used": history_used_chars,
            },
        )

        if force_doc and doc_rag_active:
            log_event(
                log,
                logging.INFO,
                ACL_MOD_CONTEXT,
                "doc_rag",
                "RAG restrito ao silo doc (MySQL)",
                metadata={"query": query},
            )
        elif force_doc:
            log_event(
                log,
                logging.INFO,
                ACL_MOD_CONTEXT,
                "doc_silo_empty_fallback_rag",
                "silo doc vazio — continua com RAG normal",
                metadata={"query": query},
            )

        # --- Retrieval bruto + política de decisão --------------------------

        catalog_result = self._catalog_match(query)
        trace_reason_override: str | None = None

        if (
            self._lesson_catalog
            and catalog_result
            and self._lesson_catalog.is_confident(catalog_result)
            and self._indexed_lesson_keys is not None
        ):
            top = self._lesson_catalog.top_lesson(catalog_result)
            if top is not None:
                lesson_key = self._lesson_catalog.lesson_key(top)
                if lesson_key not in self._indexed_lesson_keys:
                    trace_reason_override = "index_gap"
                    log_event(
                        log,
                        logging.INFO,
                        ACL_MOD_CONTEXT,
                        "index_gap_advisory",
                        "aula no catalogo ausente do indice — LLM com RAG",
                        metadata={
                            "lesson_slug": top.slug,
                            "lesson_discipline": top.discipline,
                        },
                    )

        if (
            not doc_rag_active
            and self._lesson_catalog
            and catalog_result
            and self._lesson_catalog.is_strict_confident(catalog_result)
        ):
            top_lesson = self._lesson_catalog.top_lesson(catalog_result)
            if top_lesson is not None:
                lesson_key = self._lesson_catalog.lesson_key(top_lesson)
                if lesson_key in self._indexed_lesson_keys:
                    narrowed = self._sanitize_discipline(top_lesson.discipline)
                    if narrowed is not None:
                        effective_discipline = narrowed

        domain_route: DomainRouteResult | None = None
        domain_discipline_filters: tuple[str, ...] | None = None
        domain_instruction = ""

        if (
            getattr(self._settings, "domain_router_enabled", False)
            and effective_discipline is None
            and not doc_rag_active
            and not force_doc
            and not force_rag
            and discipline_from_command is None
            and json_discipline is None
        ):
            indexed = getattr(self._search_engine, "discipline_ids", frozenset())
            self._domain_router = DomainRouter(
                indexed_disciplines=indexed if isinstance(indexed, frozenset) else frozenset(indexed),
            )
            domain_route = self._domain_router.route(
                query or llm_user_content,
                recent_context=recent_context_block,
            )
            if domain_route.fallback_global:
                log_event(
                    log,
                    logging.INFO,
                    ACL_MOD_CONTEXT,
                    "domain_router_fallback",
                    "retrieval global — domínio indeterminado ou baixa confiança",
                    metadata={
                        "reason": domain_route.reason,
                        "confidence": domain_route.confidence,
                        "candidates": [
                            {"id": c.expert_id, "score": c.score}
                            for c in domain_route.candidates
                        ],
                        "router_latency_ms": round(domain_route.router_latency_ms, 2),
                    },
                )
            elif domain_route.retrieval_scopes:
                if domain_route.multi_domain:
                    domain_discipline_filters = domain_route.retrieval_scopes
                elif len(domain_route.retrieval_scopes) == 1:
                    effective_discipline = self._sanitize_discipline(
                        domain_route.retrieval_scopes[0]
                    )
                else:
                    domain_discipline_filters = domain_route.retrieval_scopes
                if domain_route.instructions:
                    domain_instruction = domain_route.instructions
                log_event(
                    log,
                    logging.INFO,
                    ACL_MOD_CONTEXT,
                    "domain_router_scoped",
                    "retrieval restrito por domínio",
                    metadata={
                        "selected": domain_route.selected_expert,
                        "selected_experts": list(domain_route.selected_experts),
                        "confidence": domain_route.confidence,
                        "scopes": list(domain_route.retrieval_scopes),
                        "multi_domain": domain_route.multi_domain,
                        "reason": domain_route.reason,
                        "router_latency_ms": round(domain_route.router_latency_ms, 2),
                    },
                )

        if rag_skipped:
            candidates = []
            log_event(
                log,
                logging.INFO,
                ACL_MOD_CONTEXT,
                "rag_skipped_by_route",
                "BM25 dispensado neste turno (ContextRouter ou time_fact legado)",
                metadata={
                    "query": query,
                    "intent": temporal_intent.kind if temporal_intent else None,
                    "rag_skip_reason": rag_skip_reason,
                    "context_profile": (
                        route.profile.value if route is not None else None
                    ),
                },
            )
        else:
            rag_query = query
            if (
                self._settings.query_discipline_boost_enabled
                and domain_route is not None
                and not domain_route.fallback_global
                and domain_route.retrieval_scopes
            ):
                rag_query = _expand_query_with_discipline_markers(
                    query, domain_route.retrieval_scopes
                )
                if rag_query != query:
                    log_event(
                        log,
                        logging.DEBUG,
                        ACL_MOD_CONTEXT,
                        "query_discipline_boost",
                        "query BM25 enriquecida com markers de domínio",
                        metadata={
                            "scopes": list(domain_route.retrieval_scopes),
                            "rag_query_len": len(rag_query),
                        },
                    )
            candidates = self._search_engine.search_candidates(
                rag_query,
                candidate_k=self._settings.retrieval_candidate_k,
                discipline_filter=effective_discipline,
                discipline_filters=domain_discipline_filters,
            )
            if (
                domain_route is not None
                and not domain_route.fallback_global
                and not candidates
            ):
                log_event(
                    log,
                    logging.INFO,
                    ACL_MOD_CONTEXT,
                    "domain_scoped_empty_fallback",
                    "scoped retrieval vazio — fallback global",
                    metadata={
                        "scopes": list(domain_route.retrieval_scopes),
                        "selected": domain_route.selected_expert,
                    },
                )
                candidates = self._search_engine.search_candidates(
                    rag_query,
                    candidate_k=self._settings.retrieval_candidate_k,
                )
                if domain_route is not None:
                    domain_route = DomainRouteResult(
                        selected_expert=domain_route.selected_expert,
                        selected_experts=domain_route.selected_experts,
                        confidence=domain_route.confidence,
                        candidates=domain_route.candidates,
                        retrieval_scopes=domain_route.retrieval_scopes,
                        fallback_global=True,
                        multi_domain=domain_route.multi_domain,
                        reason="scoped_empty_fallback",
                        instructions=domain_route.instructions,
                        router_latency_ms=domain_route.router_latency_ms,
                    )
                    effective_discipline = None
                    domain_discipline_filters = None
            if (
                self._settings.catalog_rerank_enabled
                and catalog_result
                and self._lesson_catalog
                and self._lesson_catalog.is_confident(catalog_result)
                and candidates
            ):
                top_lesson = self._lesson_catalog.top_lesson(catalog_result)
                if top_lesson is not None:
                    lesson_key = self._lesson_catalog.lesson_key(top_lesson)
                    if lesson_key in self._indexed_lesson_keys:
                        candidates = _boost_candidates_for_catalog_lesson(
                            candidates, lesson_key
                        )
                        log_event(
                            log,
                            logging.DEBUG,
                            ACL_MOD_CONTEXT,
                            "catalog_rerank_boost",
                            "chunks da aula do catálogo promovidos no ranking",
                            metadata={
                                "lesson_key": lesson_key,
                                "catalog_top_score": catalog_result.top_score,
                            },
                        )
        max_per_source = (
            1
            if doc_rag_active
            else self._settings.retrieval_max_chunks_per_source
        )
        effective_top_k = (
            max(1, min(int(top_k), 20))
            if top_k is not None
            else self._settings.retrieval_top_k
        )
        if route is not None and route.max_rag_sources > 0:
            effective_top_k = min(effective_top_k, int(route.max_rag_sources))
        decision = build_decision(
            query=query,
            candidates=candidates,
            mode=mode,
            min_score=self._settings.retrieval_min_score,
            min_score_margin=self._settings.retrieval_min_score_margin,
            min_coverage=self._settings.retrieval_min_coverage,
            min_coverage_weighted=self._settings.retrieval_min_coverage_weighted,
            min_terms=self._settings.retrieval_min_terms,
            top_k=effective_top_k,
            max_per_source=max_per_source,
            acl_retrieval_mode=self._settings.retrieval_mode,
            disambiguation_enabled=self._settings.disambiguation_enabled,
        )
        if catalog_result and self._lesson_catalog:
            decision = self._try_catalog_rescue(query, decision, mode, catalog_result)

        # Pós-RAG: perfil NORMAL/DEEP pode omitir chunks com confidence=low.
        if (
            filter_low_confidence_rag
            and not rag_skipped
            and decision.confidence == "low"
            and decision.selected_candidates
        ):
            decision = RetrievalDecision(
                allow_generation=decision.allow_generation,
                reason=decision.reason,
                confidence=decision.confidence,
                selected_candidates=(),
                trace=decision.trace,
            )
            rag_skip_reason = RagSkipReason.LOW_CONFIDENCE_FILTER.value
            log_event(
                log,
                logging.INFO,
                ACL_MOD_CONTEXT,
                "rag_filtered_low_confidence",
                "chunks omitidos — confidence=low (ContextRouter)",
                metadata={"query": query, "reason": decision.reason},
            )

        catalog_section = (
            self._lesson_catalog.build_prompt_section(catalog_result)
            if self._lesson_catalog and catalog_result
            else ""
        )
        selected = [
            {
                "source": c.source,
                "text": c.text,
                "score": c.raw_score,
                "normalized_score": c.normalized_score,
            }
            for c in decision.selected_candidates
        ]
        grounding = _select_grounding(decision, self._settings)
        merged_chunks = _merge_pin_and_retrieval_chunks(
            pin,
            selected,
            self._settings.pinned_max_chars,
        )
        score_by_source = {str(s["source"]): s.get("normalized_score") for s in selected}
        selected_for_format = [
            {
                "source": d["source"],
                "text": d["text"],
                "normalized_score": score_by_source.get(d["source"]),
            }
            for d in merged_chunks
        ]
        # Resolução de canal/grupo para Group Memory e Group Profile
        platform = "whatsapp"
        channel_id = ""
        if session_id:
            segments = [unquote(s) for s in session_id.split(":")]
            if len(segments) >= 3:
                platform = segments[0]
                channel_id = segments[2]
            elif len(segments) == 1:
                channel_id = segments[0]

        group_profile_block = ""
        group_profile_active = False
        group_profile_topics: tuple[str, ...] = ()
        group_memory_block = ""
        group_memory_used = False
        group_memory_hits: list[dict[str, Any]] = []

        if self._group_memory_store is not None and channel_id:
            # 1. Group Profile (contexto social dinâmico)
            if getattr(self._settings, "group_profile_enabled", True):
                try:
                    p_data = self._group_memory_store.get_group_profile(platform, channel_id)
                    if p_data:
                        prof = GroupProfile.from_dict(p_data)
                        group_profile_block = prof.prompt_block()
                        if group_profile_block:
                            group_profile_active = True
                            group_profile_topics = tuple(prof.common_topics)
                except Exception as exc:
                    log.warning("Falha ao carregar group profile (%s): %s", channel_id, exc)

            # 2. Group Memory (busca histórica BM25 + recência) — query limpa, não o transcript
            router_wants_memory = (
                route is not None and route.use_group_memory
            ) if router_enabled else True
            if (
                getattr(self._settings, "group_memory_enabled", True)
                and not force_doc
                and router_wants_memory
            ):
                try:
                    max_res = getattr(self._settings, "group_memory_max_results", 5)
                    rec_w = getattr(self._settings, "group_memory_recency_weight", 0.3)
                    max_chars = getattr(self._settings, "group_memory_max_chars", 4000)
                    hist_matches = self._group_memory_store.search_historical(
                        platform,
                        channel_id,
                        query,
                        top_k=max_res,
                        recency_weight=rec_w,
                    )
                    if hist_matches:
                        group_memory_used = True
                        group_memory_hits = [
                            {
                                "message_id": h.message_id,
                                "sender": h.sender_name,
                                "timestamp": h.timestamp,
                                "content": h.content,
                                "score": round(h.final_score, 3),
                                "source_type": "group_memory",
                            }
                            for h in hist_matches
                        ]
                        lines = [
                            "## Histórico de discussões relevantes do grupo (memória conversacional — NÃO é fonte oficial)",
                        ]
                        used_chars = 0
                        for h in hist_matches:
                            date_label = h.timestamp[:10] if len(h.timestamp) >= 10 else "data recente"
                            sender = h.sender_name or "membro"
                            line = f"- [{sender} em {date_label}]: {h.content}"
                            if used_chars + len(line) > max_chars:
                                break
                            lines.append(line)
                            used_chars += len(line)
                        lines.append(
                            "Nota: As mensagens históricas acima foram enviadas por participantes no grupo e servem "
                            "como contexto de conversas passadas. Não as trate como material institucional oficial."
                        )
                        group_memory_block = "\n".join(lines)
                except Exception as exc:
                    log.warning("Falha na busca da memória histórica do grupo (%s): %s", channel_id, exc)

        ctx = _format_chunks_for_prompt(selected_for_format, decision, self._settings)
        sticky_block = _sticky_block_for_pin(self._settings, pin)
        pin_used = bool(pin and pin.chunks)
        system_content = ContextBuilder.assemble_system_content(
            SystemContextBlocks(
                base_prompt=sp,
                identity=layers.identity_block,
                institutional=layers.institutional_block,
                temporal=layers.temporal_block,
                calendar=layers.calendar_block,
                catalog_router=self._settings.catalog_router_prompt,
                catalog_section=catalog_section,
                sticky=sticky_block,
                group_profile=group_profile_block,
                behavior_advisory=behavior_advisory,
                grounding=grounding,
                domain_instruction=domain_instruction,
                chunk_context=ctx,
                group_memory=group_memory_block,
                recent_context=recent_context_block,
            )
        )

        if doc_rag_active:
            label = "Documentação (doc)"
        elif (
            domain_route is not None
            and not domain_route.fallback_global
            and domain_route.selected_expert
        ):
            if domain_route.multi_domain:
                label = f"Domínios: {', '.join(domain_route.selected_experts)}"
            elif effective_discipline is not None:
                label = _trace_label_for_discipline(effective_discipline)
            else:
                label = domain_route.selected_expert
        elif effective_discipline is not None:
            label = _trace_label_for_discipline(effective_discipline)
        else:
            label = _global_scope_label(self._settings)

        trace_sources = [d["source"] for d in merged_chunks]
        if doc_rag_active:
            scope_key = "doc"
        else:
            scope_key = self._scope_key_for_hit(
                force_rag, discipline_from_command, effective_discipline
            )
        if not skip_pin_update:
            self._save_pin(
                session_id,
                scope_key,
                [{"source": d["source"], "text": d["text"]} for d in merged_chunks],
                trace_sources,
            )

        final_reason = trace_reason_override or decision.reason
        if rag_skipped:
            # Turno respondível sem BM25 — ausência de candidatos é intencional.
            final_reason = rag_skip_reason or "temporal_fact"
        final_reason = _relax_weak_reason_for_pinned_follow_up(
            final_reason, query, pin, pin_used
        )
        scope_psk, scope_hint, scope_cmd, sources_note = _build_scope_ui_hints(
            pin,
            query,
            discipline_from_command,
            pin_used,
            sources_mix_this_turn=_retrieval_adds_sources_beyond_pin(pin, selected),
        )
        trace = ContextTrace(
            label=label,
            sources=_dedupe_sources(trace_sources),
            source_details=_build_source_details_for_ui(
                merged_chunks,
                self._lesson_catalog,
                self._settings.iss_public_lesson_base,
            ),
            pinned_active=self._pin_active(session_id),
            pinned_display=self._pin_display(session_id),
            pin_chunks_used=pin_used,
            pinned_scope_key=scope_psk,
            scope_hint=scope_hint,
            suggested_scope_command=scope_cmd,
            sources_note=sources_note,
            mode=mode,
            decision="answer",
            reason=final_reason,
            confidence=decision.confidence,
            retrieval_trace=decision.trace,
            temporal_context=(
                layers.temporal.to_trace_data() if layers.temporal is not None else None
            ),
            calendar_context=(
                {
                    "events_used": [
                        e.to_trace_data(layers.temporal.today)
                        for e in layers.calendar_events_used
                    ],
                    "events_used_count": len(layers.calendar_events_used),
                }
                if layers.temporal is not None and layers.calendar_block
                else None
            ),
            temporal_intent=(temporal_intent.kind if temporal_intent else None),
            rag_skipped=rag_skipped,
            institutional_files=layers.institutional_files,
            identity_active=bool(layers.identity_block),
            router_enabled=bool(route is not None),
            context_profile=(route.profile.value if route is not None else None),
            rag_skip_reason=rag_skip_reason,
            include_institutional=(
                route.include_institutional if route is not None else None
            ),
            include_calendar=(
                route.include_calendar if route is not None else None
            ),
            transcript_turns_requested=(
                route.transcript_max_turns if route is not None else None
            ),
            transcript_turns_used=len(history_truncated),
            router_reasons=(route.reasons if route is not None else ()),
            group_memory_used=group_memory_used,
            group_memory_hits=tuple(group_memory_hits),
            group_profile_active=group_profile_active,
            group_profile_topics=group_profile_topics,
            invocation_type=parsed_invocation.type or None,
            contextual_invocation=parsed_invocation.is_contextual,
            recent_context_count=len(parsed_invocation.recent_context),
            no_useful_context=parsed_invocation.no_useful_context,
            behavior_flags=tuple(behavior_flags),
            conversation_resolution_k=conversation_resolution_k,
            dominant_conversation_topic=dominant_conversation_topic,
            conversation_ambiguous=conversation_ambiguous,
            domain_router_enabled=getattr(self._settings, "domain_router_enabled", False),
            domain_candidates=tuple(
                {"id": c.expert_id, "score": c.score, "raw_hits": c.raw_hits}
                for c in (domain_route.candidates if domain_route else ())
            ),
            selected_domain=(
                domain_route.selected_expert if domain_route else None
            ),
            selected_domains=(
                domain_route.selected_experts if domain_route else ()
            ),
            domain_confidence=(
                domain_route.confidence if domain_route else None
            ),
            domain_retrieval_scope=(
                domain_route.retrieval_scopes if domain_route else ()
            ),
            domain_fallback=(
                domain_route.fallback_global if domain_route else False
            ),
            domain_multi=(
                domain_route.multi_domain if domain_route else False
            ),
            domain_router_reason=(
                domain_route.reason if domain_route else None
            ),
            domain_router_latency_ms=(
                round(domain_route.router_latency_ms, 2)
                if domain_route
                else None
            ),
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
                "reason": final_reason,
                "confidence": decision.confidence,
            },
        )
        return BuildMessagesResult(
            messages=_merge_messages_with_history(
                system_content, history_truncated, llm_user_content
            ),
            trace=trace,
            decision=decision,
            candidates_considered=tuple(candidates),
            effective_discipline=effective_discipline,
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
        catalog_result: CatalogMatchResult | None = None,
        catalog_match: bool = False,
        hard_stop_payload: dict | None = None,
    ) -> BuildMessagesResult:
        if reason == "index_gap":
            message = hard_stop_message(reason)
            if hard_stop_payload is None:
                hard_stop_payload = {"suggested_candidates": []}
        elif reason in _CATALOG_RESCUE_REASONS and catalog_result is not None:
            message = _enrich_hard_stop_with_catalog(reason, catalog_result)
            # Desambiguação via catálogo — nunca a aula-alvo do rescue abortado.
            hard_stop_payload = {
                "expected_lesson": None,
                "suggested_candidates": _catalog_suggested_candidates(catalog_result),
            }
        else:
            message = hard_stop_message(reason)

        label = (
            _trace_label_for_discipline(discipline)
            if discipline
            else _global_scope_label(self._settings)
        )
        trace_sources: list[str] = []
        if trace_retrieval is not None:
            trace_sources = [s["source"] for s in trace_retrieval.selected_sources]
        scope_psk, scope_hint, scope_cmd, sources_note = _build_scope_ui_hints(
            pin, query, None, False
        )
        trace = ContextTrace(
            label=label,
            sources=_dedupe_sources(trace_sources),
            pinned_active=bool(pin),
            pinned_display=pin.display_name if pin else None,
            pinned_scope_key=scope_psk,
            scope_hint=scope_hint,
            suggested_scope_command=scope_cmd,
            sources_note=sources_note,
            mode=mode,
            decision="hard_stop",
            reason=reason,
            confidence="low",
            retrieval_trace=trace_retrieval,
            catalog_match=catalog_match,
            hard_stop_payload=hard_stop_payload,
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
