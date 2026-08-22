"""Camadas de contexto do Kernel (identity, institucional, temporal, calendar).

Arquitetura: cada provider produz um bloco de texto para o system prompt e
dados estruturados para observabilidade. O `ContextBuilder` reúne os blocos
numa ordem previsível — ver docs/CONTEXT-ARCHITECTURE.md.
"""

from kernel.context.builder import ContextBuilder, ContextLayers, SystemContextBlocks
from kernel.context.calendar_provider import CalendarEvent, CalendarProvider
from kernel.context.institutional import InstitutionalContextProvider
from kernel.context.intent import TemporalIntent, detect_temporal_intent
from kernel.context.router import ContextRouter
from kernel.context.temporal import TemporalContext, TemporalContextProvider
from kernel.context.types import (
    CalendarBudgets,
    ContextProfile,
    ContextRoute,
    RagSkipReason,
    RouteSignals,
)

__all__ = [
    "CalendarBudgets",
    "CalendarEvent",
    "CalendarProvider",
    "ContextBuilder",
    "ContextLayers",
    "ContextProfile",
    "ContextRoute",
    "ContextRouter",
    "InstitutionalContextProvider",
    "RagSkipReason",
    "RouteSignals",
    "SystemContextBlocks",
    "TemporalContext",
    "TemporalContextProvider",
    "TemporalIntent",
    "detect_temporal_intent",
]
