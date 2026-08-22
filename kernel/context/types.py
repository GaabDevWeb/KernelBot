"""Tipos do contrato ContextRoute v1 — ver docs/contracts/context-route-v1.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kernel.context.intent import TemporalIntent


class ContextProfile(str, Enum):
    FAST = "FAST"
    NORMAL = "NORMAL"
    DEEP = "DEEP"


class RagSkipReason(str, Enum):
    TEMPORAL_FACT = "temporal_fact"
    GREETING_ACK = "greeting_ack"
    CALENDAR_ONLY = "calendar_only"
    PROFILE_FAST = "profile_fast"
    LOW_CONFIDENCE_FILTER = "low_confidence_filter"
    NONE = "none"


@dataclass(frozen=True)
class CalendarBudgets:
    max_events: int = 0
    max_past_events: int = 0


@dataclass(frozen=True)
class RouteSignals:
    """Sinais determinísticos de entrada do ContextRouter (sem I/O)."""

    force_doc: bool = False
    force_rag: bool = False
    discipline_from_command: str | None = None
    history_turns: int = 0
    temporal_intent: TemporalIntent | None = None
    chat_history_max_turns: int = 12


@dataclass(frozen=True)
class ContextRoute:
    """Decisão de montagem de contexto para um turno (contrato v1)."""

    profile: ContextProfile
    include_identity: bool = True
    include_temporal: bool = True
    include_institutional: bool = False
    institutional_files: tuple[str, ...] = ()
    include_calendar: bool = False
    calendar_budgets: CalendarBudgets = field(default_factory=CalendarBudgets)
    rag_skipped: bool = False
    rag_skip_reason: RagSkipReason = RagSkipReason.NONE
    transcript_max_turns: int = 0
    max_rag_sources: int = 0
    filter_low_confidence_rag: bool = False
    reasons: tuple[str, ...] = ()
