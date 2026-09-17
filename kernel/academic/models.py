"""Modelos do catálogo académico estrutural (aulas, disciplinas, avaliações)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class AcademicReferenceKind(str, Enum):
    FIRST = "first"
    LAST = "last"
    BY_ORDER = "by_order"
    PREVIOUS = "previous"
    NEXT = "next"
    BY_SLUG = "by_slug"
    LINK = "link"
    ASSESSMENT = "assessment"
    MANUAL = "manual"


class AcademicIntent(str, Enum):
    LINK_ONLY = "link_only"
    CONTENT = "content"
    NAVIGATION = "navigation"
    LIST = "list"
    ASSESSMENT_LOOKUP = "assessment_lookup"
    ASSESSMENT_EXPLAIN = "assessment_explain"
    NONE = "none"


@dataclass(frozen=True)
class AcademicLesson:
    discipline: str
    slug: str
    title: str
    order: int
    source: str
    url: str | None = None


@dataclass(frozen=True)
class AcademicDiscipline:
    id: str
    label: str
    lesson_count: int
    lessons: tuple[AcademicLesson, ...] = ()


@dataclass(frozen=True)
class AssessmentEntry:
    """Entrada de TP/AT/Assessment/Entrega indexada a partir de markdown real."""

    id: str
    discipline: str
    kind: str  # tp | at | assessment | entrega
    number: int | None
    title: str
    slug: str | None = None
    url: str | None = None
    source: str | None = None
    content_path: str | None = None
    due_date: str | None = None

    def read_content(self, *, max_chars: int = 12_000) -> str:
        if not self.content_path:
            return ""
        path = Path(self.content_path)
        if not path.is_file():
            return ""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return ""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."


@dataclass(frozen=True)
class AcademicResolveResult:
    """Resultado determinístico de uma referência académica."""

    resolved: bool
    intent: AcademicIntent = AcademicIntent.NONE
    reference_kind: AcademicReferenceKind | None = None
    discipline: str | None = None
    lesson: AcademicLesson | None = None
    assessment: AssessmentEntry | None = None
    ambiguous: bool = False
    missing_data: bool = False
    reason: str = ""
    prompt_block: str = ""
    router: str = "academic_catalog"
    metadata: dict = field(default_factory=dict)
