"""ContextBuilder — montagem previsível do system prompt em camadas.

Ordem canônica das camadas (ver docs/CONTEXT-ARCHITECTURE.md):

    1. base_prompt      (kernel/policies/systemPrompt/system_prompt.txt)
    2. identity         (kernel/policies/systemPrompt/identity.txt)
    3. institutional    (context/*.md preenchidos pelo operador)
    4. temporal         (data/hora do servidor)
    5. calendar         (agenda acadêmica com deltas calculados)
    6. catalog_router + catalog_section  (catálogo de aulas — existente)
    7. sticky           (contexto fixado — existente)
    8. grounding        (contrato anti-alucinação — existente)
    9. chunk_context    (trechos RAG [Fonte: …] — existente)

Blocos vazios são omitidos. Nenhuma outra parte do código deve concatenar
system prompt por conta própria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kernel.context.calendar_provider import CalendarEvent, CalendarProvider
from kernel.context.institutional import InstitutionalContextProvider
from kernel.context.temporal import TemporalContext, TemporalContextProvider

if TYPE_CHECKING:
    from kernel.context.types import ContextRoute


@dataclass(frozen=True)
class SystemContextBlocks:
    """Blocos de texto prontos, na ordem canônica de montagem."""

    base_prompt: str = ""
    identity: str = ""
    institutional: str = ""
    temporal: str = ""
    calendar: str = ""
    catalog_router: str = ""
    catalog_section: str = ""
    sticky: str = ""
    group_profile: str = ""
    grounding: str = ""
    chunk_context: str = ""
    group_memory: str = ""
    recent_context: str = ""


@dataclass(frozen=True)
class ContextLayers:
    """Camadas novas resolvidas para um turno + dados de observabilidade."""

    identity_block: str = ""
    institutional_block: str = ""
    temporal_block: str = ""
    calendar_block: str = ""
    group_profile_block: str = ""
    temporal: TemporalContext | None = None
    calendar_events_used: tuple[CalendarEvent, ...] = ()
    institutional_files: tuple[str, ...] = field(default_factory=tuple)


class ContextBuilder:
    """Resolve as camadas novas (identity/institucional/temporal/calendar)
    e monta o system prompt final numa ordem única e previsível."""

    def __init__(
        self,
        *,
        identity_prompt: str = "",
        institutional: InstitutionalContextProvider | None = None,
        temporal: TemporalContextProvider | None = None,
        calendar: CalendarProvider | None = None,
    ) -> None:
        self._identity_prompt = (identity_prompt or "").strip()
        self._institutional = institutional
        self._temporal = temporal
        self._calendar = calendar

    def build_layers(self, *, route: ContextRoute | None = None) -> ContextLayers:
        """Resolve camadas. `route is None` → comportamento legado (always-on)."""
        identity_block = self._identity_prompt
        if route is not None and not route.include_identity:
            identity_block = ""

        institutional_block = ""
        institutional_files: tuple[str, ...] = ()
        if self._institutional is not None:
            if route is None:
                institutional_block, institutional_files = (
                    self._institutional.prompt_block()
                )
            elif route.include_institutional:
                institutional_block, institutional_files = (
                    self._institutional.prompt_block(files=route.institutional_files)
                )
            # else: bloco vazio (FAST / off)

        temporal: TemporalContext | None = None
        temporal_block = ""
        if self._temporal is not None:
            if route is None or route.include_temporal:
                temporal = self._temporal.now()
                temporal_block = temporal.prompt_block()

        calendar_block = ""
        events_used: tuple[CalendarEvent, ...] = ()
        if self._calendar is not None and temporal is not None:
            if route is None:
                calendar_block, events_used = self._calendar.build_prompt_block(
                    temporal
                )
            elif route.include_calendar:
                max_events = int(route.calendar_budgets.max_events)
                max_past = int(route.calendar_budgets.max_past_events)
                if max_events > 0 or max_past > 0:
                    calendar_block, events_used = self._calendar.build_prompt_block(
                        temporal,
                        max_events=max_events,
                        max_past_events=max_past,
                    )
                # caps 0 → bloco vazio, events ()
            # include_calendar false → bloco vazio

        return ContextLayers(
            identity_block=identity_block,
            institutional_block=institutional_block,
            temporal_block=temporal_block,
            calendar_block=calendar_block,
            temporal=temporal,
            calendar_events_used=events_used,
            institutional_files=institutional_files,
        )

    @staticmethod
    def assemble_system_content(blocks: SystemContextBlocks) -> str:
        parts: list[str] = [
            blocks.base_prompt,
            blocks.identity,
            blocks.institutional,
            blocks.temporal,
            blocks.calendar,
        ]
        if blocks.catalog_section:
            parts.append(blocks.catalog_router)
            parts.append(blocks.catalog_section)
        parts.append(blocks.sticky)
        parts.append(blocks.group_profile)
        parts.append(blocks.grounding)
        parts.append(blocks.chunk_context)
        parts.append(blocks.recent_context)
        parts.append(blocks.group_memory)
        return "\n\n".join(p for p in parts if p)
