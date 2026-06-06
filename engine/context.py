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
from engine.lesson_catalog import CatalogMatchResult, LessonCatalog, LessonEntry
from engine.pinned_store import PinnedContext, PinnedSessionStore
from engine.retrieval import (
    RetrievalCandidate,
    RetrievalDecision,
    RetrievalTrace,
    build_decision,
    extract_informative_terms,
    select_mode,
)
from engine.search import SearchEngine

_CATALOG_RESCUE_REASONS: frozenset[str] = frozenset({"ambiguous_retrieval"})

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
    "index_gap": (
        "Identifiquei no catálogo uma aula que corresponde à sua pergunta, mas o conteúdo "
        "ainda não está disponível no índice de busca local.\n\n"
        "O tópico consta no currículo e a indexação deve ser atualizada em breve. "
        "Tente novamente após `/reload` ou avise o responsável."
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


_PYTHON_QUERY_MARKERS = (
    "jupyter",
    "variável",
    "variavel",
    "f-string",
    "fstring",
    "python",
    "elif",
    "snake_case",
    "nameerror",
    "enumerate",
    "lista",
    "laço",
    "laco",
    "print(",
    "for ",
)

_SQL_QUERY_MARKERS = (
    "looker",
    "group by",
    "groupby",
    "dashboard",
    "having",
    " duplicata",
    "sql",
    " join ",
    "select ",
    "cafeteria",
)

_CARREIRA_QUERY_MARKERS = (
    "competência",
    "competencia",
    "avaliação por",
    "avaliacao por",
    "carreira",
    "estágio",
    "estagio",
    "linkedin",
    "rubrica",
    "entrevista",
    "currículo",
    "curriculo",
    "oratória",
    "oratoria",
    "soft skill",
    "estágio de",
)

_PROJETO_BLOCO_QUERY_MARKERS = (
    "placeholder",
    "commit()",
    "crud",
    "mini-projeto",
    "mini projeto",
    "projeto de bloco",
    "projeto-bloco",
    "ingestão csv",
    "ingestao csv",
    "postgresql",
    "mysql",
    "sql server",
    "modelagem conceitual",
    "ecommerce",
    "e-commerce",
)

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
        "python": sum(1 for m in _PYTHON_QUERY_MARKERS if m in q),
        "visualizacao-sql": sum(1 for m in _SQL_QUERY_MARKERS if m in q),
        "planejamento-curso-carreira": sum(1 for m in _CARREIRA_QUERY_MARKERS if m in q),
        "projeto-bloco": sum(1 for m in _PROJETO_BLOCO_QUERY_MARKERS if m in q),
    }
    best_score = max(scores.values())
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


def _should_skip_pin_update(query: str, *, did_reset: bool) -> bool:
    """Evita fixar pin após reset, confirmação de reset ou turnos adversariais."""
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
        if use_numbered:
            if score is not None:
                header = f"[Fonte {i}: {src} | Score: {float(score):.2f}]"
            else:
                header = f"[Fonte {i}: {src}]"
        elif score is not None:
            header = f"[Fonte: {src} | Score: {float(score):.2f}]"
        else:
            header = f"[Fonte: {src}]"
        parts.append(f"{header}\n{text}")
    return "\n\n---\n\n".join(parts)


def _assemble_system_content(
    base_prompt: str,
    catalog_router: str,
    catalog_section: str,
    grounding: str,
    chunk_context: str,
    *,
    sticky_block: str = "",
) -> str:
    parts = [base_prompt]
    if catalog_section:
        parts.append(catalog_router)
        parts.append(catalog_section)
    if sticky_block:
        parts.append(sticky_block)
    parts.append(grounding)
    if chunk_context:
        parts.append(chunk_context)
    return "\n\n".join(parts)


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
    ) -> None:
        self._settings = settings
        self._search_engine = search_engine
        self._pinned_store = pinned_store
        self._lesson_catalog = lesson_catalog
        self._indexed_lesson_keys = indexed_lesson_keys or frozenset()

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
            effective_discipline = self._sanitize_discipline(
                _pin_inherited_discipline_filter(query, pin)
            )
        else:
            effective_discipline = None

        skip_pin_update = _should_skip_pin_update(query, did_reset=did_reset)

        history_in = conversation_history or []
        history_truncated = _truncate_conversation_history(
            history_in,
            max_turns=self._settings.chat_history_max_turns,
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
                catalog_result = self._catalog_match(query)
                catalog_section = (
                    self._lesson_catalog.build_prompt_section(catalog_result)
                    if self._lesson_catalog and catalog_result
                    else ""
                )
                doc_candidates = tuple(
                    RetrievalCandidate(
                        source=str(c["source"]),
                        chunk_id=f"doc-{i}",
                        text=str(c["text"]),
                        discipline="doc",
                        raw_score=1.0,
                        normalized_score=1.0,
                        matched_terms=(),
                    )
                    for i, c in enumerate(doc_chunks)
                )
                doc_decision = RetrievalDecision(
                    allow_generation=True,
                    reason="ok",
                    confidence="high",
                    selected_candidates=doc_candidates,
                    trace=RetrievalTrace(
                        query=query,
                        normalized_query=query,
                        informative_terms=(),
                        mode=mode,
                    ),
                )
                doc_selected = [
                    {"source": str(c["source"]), "text": str(c["text"])}
                    for c in doc_chunks
                ]
                merged_doc = _merge_pin_and_retrieval_chunks(
                    pin,
                    doc_selected,
                    self._settings.pinned_max_chars,
                )
                ctx = _join_chunks_for_prompt(merged_doc)
                grounding = _select_grounding(doc_decision, self._settings)
                sticky_block = _sticky_block_for_pin(self._settings, pin)
                pin_used = bool(pin and pin.chunks)
                system_content = _assemble_system_content(
                    sp,
                    self._settings.catalog_router_prompt,
                    catalog_section,
                    grounding,
                    ctx,
                    sticky_block=sticky_block,
                )
                trace_sources = [d["source"] for d in merged_doc]
                pin_chunks = [{"source": d["source"], "text": d["text"]} for d in merged_doc]
                if not skip_pin_update:
                    self._save_pin(session_id, "doc", pin_chunks, trace_sources)
                scope_psk, scope_hint, scope_cmd, sources_note = _build_scope_ui_hints(
                    pin,
                    query,
                    discipline_from_command,
                    pin_used,
                    sources_mix_this_turn=_retrieval_adds_sources_beyond_pin(
                        pin, doc_selected
                    ),
                )
                trace = ContextTrace(
                    label="Documentação (doc)",
                    sources=_dedupe_sources(trace_sources),
                    pinned_active=self._pin_active(session_id),
                    pinned_display=self._pin_display(session_id),
                    pin_chunks_used=pin_used,
                    pinned_scope_key=scope_psk,
                    scope_hint=scope_hint,
                    suggested_scope_command=scope_cmd,
                    sources_note=sources_note,
                    mode=mode,
                    decision="answer",
                    reason="ok",
                    confidence="high",
                )
                return BuildMessagesResult(
                    messages=_merge_messages_with_history(
                        system_content, history_truncated, query
                    ),
                    trace=trace,
                )
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
            self._lesson_catalog
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
            acl_retrieval_mode=self._settings.retrieval_mode,
            disambiguation_enabled=self._settings.disambiguation_enabled,
        )
        if catalog_result and self._lesson_catalog:
            decision = self._try_catalog_rescue(query, decision, mode, catalog_result)

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
        ctx = _format_chunks_for_prompt(selected_for_format, decision, self._settings)
        sticky_block = _sticky_block_for_pin(self._settings, pin)
        pin_used = bool(pin and pin.chunks)
        system_content = _assemble_system_content(
            sp,
            self._settings.catalog_router_prompt,
            catalog_section,
            grounding,
            ctx,
            sticky_block=sticky_block,
        )

        if effective_discipline is not None:
            label = _trace_label_for_discipline(effective_discipline)
        elif force_rag:
            label = _global_scope_label(self._settings)
        else:
            label = _global_scope_label(self._settings)

        trace_sources = [d["source"] for d in merged_chunks]
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
                system_content, history_truncated, query
            ),
            trace=trace,
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
