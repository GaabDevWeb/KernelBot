"""Detecção de intenções académicas estruturais (ordem, links, TP/AT)."""

from __future__ import annotations

import re

from kernel.academic.models import AcademicIntent, AcademicReferenceKind

_LINK_RE = re.compile(
    r"\b(?:link|url|manda(?:r)?(?:\s+o)?\s+link|envia(?:r)?(?:\s+o)?\s+link)\b",
    re.IGNORECASE,
)
_ORDINAL_WORDS = {
    "primeira": 1,
    "primeiro": 1,
    "1ª": 1,
    "1a": 1,
    "segunda": 2,
    "segundo": 2,
    "2ª": 2,
    "2a": 2,
    "terceira": 3,
    "terceiro": 3,
    "3ª": 3,
    "3a": 3,
    "quarta": 4,
    "quarto": 4,
    "4ª": 4,
    "4a": 4,
    "quinta": 5,
    "quinto": 5,
    "5ª": 5,
    "5a": 5,
}
_FIRST_RE = re.compile(r"\b(?:primeir[ao]|1ª|1a)\s+aula\b", re.IGNORECASE)
_LAST_RE = re.compile(r"\b(?:últim[ao]|ultim[ao])\s+aula\b", re.IGNORECASE)
_PREV_RE = re.compile(
    r"\b(?:aula\s+)?(?:anterior|passada|que\s+veio\s+antes|veio\s+antes)\b",
    re.IGNORECASE,
)
_NEXT_RE = re.compile(
    r"\b(?:próxim[ao]|proxim[ao]|seguinte)\s+aula\b|\baula\s+(?:seguinte|próxima|proxima)\b",
    re.IGNORECASE,
)
_LESSON_NUM_RE = re.compile(
    r"\baula\s+(?:n[ºo°]?\s*)?(\d{1,2})\b",
    re.IGNORECASE,
)
_TP_RE = re.compile(
    r"\b(?:tp\s*(\d+)|trabalho\s+pr[áa]tico\s*(\d+))\b",
    re.IGNORECASE,
)
_AT_RE = re.compile(
    r"\b(?:at\s*(\d+)|atividade\s+(?:te[óo]rica\s+)?(\d+))\b",
    re.IGNORECASE,
)
_ASSESSMENT_RE = re.compile(r"\bassessment\b", re.IGNORECASE)
_AT_BARE_RE = re.compile(
    r"\b(?:at\b|atividade\s+te[óo]rica\b)(?!\s*\d)",
    re.IGNORECASE,
)
_ENTREGA_RE = re.compile(
    r"\bentrega(?:\s+(?:de\s+)?projeto)?\b",
    re.IGNORECASE,
)
_EXPLAIN_RE = re.compile(
    r"\b(?:"
    r"explica(?:r)?|resum(?:a|e|ir)|"
    r"o\s+que\s+(?:foi|veio|tem|vimos|e\s+cobrad[oa]|cobra|preciso|devo|tenho)|"
    r"conte[úu]do|cobrad[oa]|cobra|cobrar|enunciado|pede|pedido|detalh(?:e|a|es|ar)"
    r")\b",
    re.IGNORECASE,
)
_ASSESSMENT_ITEM_RE = re.compile(
    r"\b(?:quest(?:ao|ão)|exerc[íi]cio|parte)\s*(\d+)\b",
    re.IGNORECASE,
)


def detect_academic_intent(query: str) -> AcademicIntent:
    q = (query or "").strip()
    if not q:
        return AcademicIntent.NONE
    if _TP_RE.search(q) or _AT_RE.search(q) or _ASSESSMENT_RE.search(q) or _AT_BARE_RE.search(q) or _ENTREGA_RE.search(q):
        if _EXPLAIN_RE.search(q) or _ASSESSMENT_ITEM_RE.search(q):
            return AcademicIntent.ASSESSMENT_EXPLAIN
        return AcademicIntent.ASSESSMENT_LOOKUP
    if _ASSESSMENT_ITEM_RE.search(q):
        return AcademicIntent.ASSESSMENT_EXPLAIN
    if _LINK_RE.search(q) and (
        _LESSON_NUM_RE.search(q) or _FIRST_RE.search(q) or _LAST_RE.search(q)
    ):
        return AcademicIntent.LINK_ONLY
    if _LINK_RE.search(q):
        return AcademicIntent.LINK_ONLY
    if _PREV_RE.search(q) or _NEXT_RE.search(q):
        return AcademicIntent.NAVIGATION
    if _FIRST_RE.search(q) or _LAST_RE.search(q) or _LESSON_NUM_RE.search(q):
        if _EXPLAIN_RE.search(q):
            return AcademicIntent.CONTENT
        return AcademicIntent.NAVIGATION
    if _EXPLAIN_RE.search(q) and re.search(r"\baula\b", q, re.IGNORECASE):
        return AcademicIntent.CONTENT
    return AcademicIntent.NONE


def parse_lesson_reference(query: str) -> tuple[AcademicReferenceKind | None, int | None]:
    q = (query or "").lower()
    if _FIRST_RE.search(q):
        return AcademicReferenceKind.FIRST, 1
    if _LAST_RE.search(q):
        return AcademicReferenceKind.LAST, None
    if _PREV_RE.search(q):
        return AcademicReferenceKind.PREVIOUS, None
    if _NEXT_RE.search(q):
        return AcademicReferenceKind.NEXT, None
    m = _LESSON_NUM_RE.search(q)
    if m:
        return AcademicReferenceKind.BY_ORDER, int(m.group(1))
    for word, num in _ORDINAL_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\s+aula\b", q):
            return AcademicReferenceKind.BY_ORDER, num
    if detect_academic_intent(query) == AcademicIntent.LINK_ONLY:
        m2 = _LESSON_NUM_RE.search(q)
        if m2:
            return AcademicReferenceKind.LINK, int(m2.group(1))
    return None, None


def parse_assessment_reference(query: str) -> tuple[str, int | None] | None:
    q = query or ""
    m = _TP_RE.search(q)
    if m:
        num = m.group(1) or m.group(2)
        return "tp", int(num) if num else None
    m = _AT_RE.search(q)
    if m:
        num = m.group(1) or m.group(2)
        return "at", int(num) if num else None
    if _ENTREGA_RE.search(q):
        return "entrega", None
    if _ASSESSMENT_RE.search(q) or _AT_BARE_RE.search(q):
        return "assessment", None
    return None


def parse_assessment_item(query: str) -> int | None:
    """Número de questão/exercício/parte referenciado (ex.: 'questão 2')."""
    m = _ASSESSMENT_ITEM_RE.search(query or "")
    return int(m.group(1)) if m else None
