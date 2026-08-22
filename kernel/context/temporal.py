"""Contexto temporal do servidor — data/hora oficiais do Kernel.

O tempo é sempre obtido pelo relógio do servidor (nunca do cliente) e
convertido para o timezone configurado (`KERNEL_TIMEZONE`, default
`America/Sao_Paulo`). O LLM recebe estes dados prontos e não deve ser
responsável por descobrir "que dia é hoje".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "America/Sao_Paulo"

# datetime.weekday(): 0 = segunda-feira.
_WEEKDAYS_PT = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)

_MONTHS_PT = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def weekday_name_pt(day: date) -> str:
    return _WEEKDAYS_PT[day.weekday()]


def month_name_pt(day: date) -> str:
    return _MONTHS_PT[day.month - 1]


def format_date_pt(day: date) -> str:
    """Ex.: 'sexta-feira, 8 de agosto de 2026'."""
    return f"{weekday_name_pt(day)}, {day.day} de {month_name_pt(day)} de {day.year}"


@dataclass(frozen=True)
class TemporalContext:
    """Snapshot imutável do 'agora' do servidor, num timezone concreto."""

    now: datetime  # timezone-aware, já no timezone configurado
    timezone_name: str

    @property
    def today(self) -> date:
        return self.now.date()

    @property
    def date_iso(self) -> str:
        return self.today.isoformat()

    @property
    def time_hm(self) -> str:
        return self.now.strftime("%H:%M")

    @property
    def weekday_name(self) -> str:
        return weekday_name_pt(self.today)

    @property
    def timestamp_iso(self) -> str:
        return self.now.isoformat(timespec="seconds")

    def prompt_block(self) -> str:
        return (
            "## Contexto temporal (dados oficiais do servidor)\n\n"
            f"- Data de hoje: {format_date_pt(self.today)} ({self.date_iso})\n"
            f"- Hora atual: {self.time_hm} (timezone: {self.timezone_name})\n"
            f"- Timestamp: {self.timestamp_iso}\n\n"
            "Estes dados são calculados pelo servidor e são a fonte oficial e "
            "definitiva para \"hoje\", \"agora\", dia da semana e qualquer "
            "referência temporal. Use-os diretamente, mesmo sem trechos "
            "[Fonte: …]. Quando o sistema fornecer contagens de dias já "
            "calculadas, use os valores fornecidos em vez de recalcular."
        )

    def to_trace_data(self) -> dict:
        return {
            "date": self.date_iso,
            "time": self.time_hm,
            "weekday": self.weekday_name,
            "timezone": self.timezone_name,
            "timestamp": self.timestamp_iso,
        }


class TemporalContextProvider:
    """Fornece o 'agora' do servidor. `clock` é injetável para testes."""

    def __init__(
        self,
        timezone_name: str = DEFAULT_TIMEZONE,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._timezone_name = timezone_name
        self._tzinfo = ZoneInfo(timezone_name)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @property
    def timezone_name(self) -> str:
        return self._timezone_name

    def now(self) -> TemporalContext:
        raw = self._clock()
        if raw.tzinfo is None:
            raw = raw.replace(tzinfo=timezone.utc)
        return TemporalContext(
            now=raw.astimezone(self._tzinfo),
            timezone_name=self._timezone_name,
        )
