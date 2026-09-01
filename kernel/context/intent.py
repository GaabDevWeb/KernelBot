"""Detecção leve de intents temporais (sem LLM).

Diferencia:

- ``time_fact`` — pergunta factual pura sobre o relógio/calendário civil
  ("que dia é hoje?", "que horas são?"). Respondível apenas com o contexto
  temporal do servidor → o RAG é dispensável nestes turnos.
- ``calendar_fact`` — pergunta sobre eventos acadêmicos no tempo ("hoje tem
  aula?", "quando é a prova?"). Prioriza agenda + contexto temporal; o RAG
  é dispensado quando a pergunta é só calendário/agenda (ver ContextRouter
  e ``is_calendar_priority_query``).

Perguntas sem marcador temporal retornam ``None`` e seguem o fluxo normal.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

TemporalIntentKind = Literal["time_fact", "calendar_fact"]


@dataclass(frozen=True)
class TemporalIntent:
    kind: TemporalIntentKind
    matched_pattern: str


def _normalize(text: str) -> str:
    """minúsculas + sem acentos, para regexes estáveis em PT-BR."""
    lowered = (text or "").strip().lower()
    decomposed = unicodedata.normalize("NFKD", lowered)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


_TIME_FACT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        r"\bque\s+dia\s+(e|eh)\s+hoje\b",
        r"\bhoje\s+(e|eh)\s+que\s+dia\b",
        r"\bque\s+horas?\s+(sao|e|eh)\b",
        r"\bqual\s+(e|eh)?\s*a?\s*data\s+(de\s+)?hoje\b",
        r"\bque\s+dia\s+(da\s+semana\s+)?(e|eh)\s+(hoje|amanha)\b",
        r"\bdata\s+atual\b",
        r"\bhora\s+atual\b",
        r"\bque\s+dia\s+do\s+mes\b",
    )
)

_CALENDAR_TERMS = (
    r"(prova|provas|avaliacao|avaliacoes|entrega|entregas|trabalho|trabalhos|"
    r"seminario|seminarios|at|ats|aula|aulas|evento|eventos|prazo|prazos)"
)

_CALENDAR_FACT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        r"\bproxim[ao]s?\s+" + _CALENDAR_TERMS,
        r"\bquando\s+(e|eh|sera|vai\s+ser)\b.*\b" + _CALENDAR_TERMS,
        r"\bquantos?\s+dias?\s+falta",
        r"\bquantas?\s+horas?\s+falta",
        r"\btem\s+" + _CALENDAR_TERMS + r"\s+(hoje|amanha|(essa|esta|nessa|nesta)\s+semana)\b",
        r"\b(hoje|amanha)\s+tem\s+" + _CALENDAR_TERMS,
        r"\b(hoje|amanha)\s+tem\s+(tp|tps|at|ats)\b",
        r"\bo\s+que\s+(temos|tem|acontece|vai\s+acontecer)\s+hoje\b",
        r"\bo\s+que\s+(temos|tem|acontece|vai\s+acontecer)\s+(essa|esta|nessa|nesta)\s+semana\b",
        r"\bo\s+que\s+(preciso|tenho)\s+(de\s+)?entregar\s+hoje\b",
        r"\bqual\s+(e|eh)\s+a\s+aula\s+(de\s+)?hoje\b",
        r"\bqual\s+(e|eh)\s+a\s+aula\s+de\s+(hoje|amanha)\b",
        r"\b(o\s+que|qual)\s+.*\b(temos|tem)\s+hoje\b",
        r"\bo\s+que\s+(aconteceu|teve|tivemos)\s+ontem\b",
        r"\bqual\s+(e|eh)\s+a\s+proxima\b",
        r"\bfalta\s+quantos?\s+dias?\b",
        r"\bagenda\s+(da\s+semana|de\s+hoje|academica)\b",
        r"\btem\s+(tp|tps|at|ats)\s+(para\s+)?entregar\b",
        r"\b(tp|tps|at|ats)\s+(temos|tem)\s+(para\s+)?entregar\b",
        r"\bqual\s+tp\s+(e|eh|tem|temos)\b",
        r"\bhoje\s+tem\s+(java|python|sql|c#|csharp|backend)\b",
    )
)


def detect_temporal_intent(query: str) -> TemporalIntent | None:
    normalized = _normalize(query)
    if not normalized:
        return None
    for pattern in _TIME_FACT_PATTERNS:
        if pattern.search(normalized):
            return TemporalIntent(kind="time_fact", matched_pattern=pattern.pattern)
    for pattern in _CALENDAR_FACT_PATTERNS:
        if pattern.search(normalized):
            return TemporalIntent(kind="calendar_fact", matched_pattern=pattern.pattern)
    return None


def is_calendar_priority_query(query: str) -> bool:
    """True quando a pergunta deve priorizar agenda/temporal sobre RAG BM25."""
    intent = detect_temporal_intent(query)
    return intent is not None and intent.kind == "calendar_fact"
