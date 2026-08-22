"""CalendarProvider — eventos acadêmicos estruturados (avaliações, entregas…).

Fonte de dados: JSON em `KERNEL_CALENDAR_PATH` (default `context/calendar.json`):

    {
      "events": [
        {
          "id": "event-001",
          "title": "AT Banco de Dados",
          "type": "assessment",
          "discipline": "Banco de Dados",
          "date": "2026-09-15",
          "time": "19:00",
          "description": "",
          "source": "official"
        }
      ]
    }

Toda a matemática temporal (dias que faltam, "é amanhã", "foi ontem") é
calculada aqui, no backend — o LLM recebe os resultados prontos no bloco
de prompt e nunca é responsável pelo cálculo.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from kernel.context.temporal import TemporalContext, format_date_pt, weekday_name_pt

log = logging.getLogger(f"kernelbots.{__name__}")

# Rótulos PT-BR para tipos conhecidos; tipos desconhecidos passam como estão.
_TYPE_LABELS_PT: dict[str, str] = {
    "assessment": "avaliação",
    "exam": "prova",
    "test": "prova",
    "at": "AT",
    "assignment": "trabalho",
    "delivery": "entrega",
    "seminar": "seminário",
    "class": "aula",
    "event": "evento",
    "holiday": "feriado",
}

# Tipos que contam como "avaliação" em consultas do tipo "próxima prova/AT".
ASSESSMENT_TYPES: frozenset[str] = frozenset({"assessment", "exam", "test", "at"})


def event_type_label(event_type: str) -> str:
    return _TYPE_LABELS_PT.get((event_type or "").strip().lower(), event_type or "evento")


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    title: str
    date: date
    type: str = "event"
    discipline: str | None = None
    time: str | None = None  # "HH:MM" ou None
    description: str = ""
    source: str = "official"

    def days_from(self, today: date) -> int:
        """Diferença em dias calculada pelo backend (negativo = passado)."""
        return (self.date - today).days

    def to_trace_data(self, today: date) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "discipline": self.discipline,
            "date": self.date.isoformat(),
            "time": self.time,
            "days_delta": self.days_from(today),
            "source": self.source,
        }


def _delta_text(days: int) -> str:
    """Texto humano para a diferença de dias — calculado pelo servidor."""
    if days == 0:
        return "é HOJE"
    if days == 1:
        return "é AMANHÃ (falta 1 dia)"
    if days > 1:
        return f"faltam {days} dias"
    if days == -1:
        return "foi ONTEM (há 1 dia)"
    return f"foi há {-days} dias"


def _parse_event(raw: object, index: int) -> CalendarEvent | None:
    if not isinstance(raw, dict):
        log.warning("calendar: evento #%d ignorado (não é objeto)", index)
        return None
    title = str(raw.get("title") or "").strip()
    raw_date = str(raw.get("date") or "").strip()
    if not title or not raw_date:
        log.warning("calendar: evento #%d ignorado (title/date obrigatórios)", index)
        return None
    try:
        event_date = date.fromisoformat(raw_date)
    except ValueError:
        log.warning(
            "calendar: evento #%d ignorado (date inválida: %r; use YYYY-MM-DD)",
            index,
            raw_date,
        )
        return None
    raw_time = raw.get("time")
    time_str = str(raw_time).strip() if raw_time else None
    discipline = str(raw.get("discipline") or "").strip() or None
    return CalendarEvent(
        id=str(raw.get("id") or f"event-{index:03d}").strip(),
        title=title,
        date=event_date,
        type=str(raw.get("type") or "event").strip().lower() or "event",
        discipline=discipline,
        time=time_str,
        description=str(raw.get("description") or "").strip(),
        source=str(raw.get("source") or "official").strip() or "official",
    )


class CalendarProvider:
    """Carrega e consulta eventos acadêmicos. Tolerante a ficheiro ausente."""

    def __init__(self, calendar_path: Path | str | None) -> None:
        self._path = Path(calendar_path) if calendar_path else None
        self._events: tuple[CalendarEvent, ...] = ()
        self._mtime: float | None = None
        self._load()

    # --- Carregamento -----------------------------------------------------

    def _load(self) -> None:
        if self._path is None or not self._path.is_file():
            self._events = ()
            self._mtime = None
            return
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("calendar: falha ao ler %s (%s) — agenda vazia", self._path, exc)
            self._events = ()
            self._mtime = None
            return
        raw_events = payload.get("events") if isinstance(payload, dict) else payload
        events: list[CalendarEvent] = []
        if isinstance(raw_events, list):
            for i, raw in enumerate(raw_events):
                ev = _parse_event(raw, i)
                if ev is not None:
                    events.append(ev)
        events.sort(key=lambda e: (e.date, e.time or "", e.title))
        self._events = tuple(events)
        try:
            self._mtime = self._path.stat().st_mtime
        except OSError:
            self._mtime = None

    def _refresh_if_changed(self) -> None:
        """Recarrega quando o ficheiro muda (operador edita sem reiniciar)."""
        if self._path is None:
            return
        try:
            mtime = self._path.stat().st_mtime if self._path.is_file() else None
        except OSError:
            mtime = None
        if mtime != self._mtime:
            self._load()

    @property
    def events(self) -> tuple[CalendarEvent, ...]:
        self._refresh_if_changed()
        return self._events

    # --- Consultas (matemática no backend) ---------------------------------

    def upcoming(
        self,
        today: date,
        *,
        types: frozenset[str] | None = None,
        discipline: str | None = None,
        limit: int | None = None,
    ) -> tuple[CalendarEvent, ...]:
        out = [
            e
            for e in self.events
            if e.date >= today
            and (types is None or e.type in types)
            and (discipline is None or _discipline_matches(e, discipline))
        ]
        return tuple(out[:limit] if limit else out)

    def next_event(
        self,
        today: date,
        *,
        types: frozenset[str] | None = None,
        discipline: str | None = None,
    ) -> CalendarEvent | None:
        found = self.upcoming(today, types=types, discipline=discipline, limit=1)
        return found[0] if found else None

    def next_assessment(self, today: date, *, discipline: str | None = None) -> CalendarEvent | None:
        return self.next_event(today, types=ASSESSMENT_TYPES, discipline=discipline)

    def events_between(self, start: date, end: date) -> tuple[CalendarEvent, ...]:
        return tuple(e for e in self.events if start <= e.date <= end)

    def events_on(self, day: date) -> tuple[CalendarEvent, ...]:
        return self.events_between(day, day)

    def events_for_discipline(self, discipline: str) -> tuple[CalendarEvent, ...]:
        return tuple(e for e in self.events if _discipline_matches(e, discipline))

    @staticmethod
    def days_until(event: CalendarEvent, today: date) -> int:
        return event.days_from(today)

    # --- Bloco de prompt ----------------------------------------------------

    def build_prompt_block(
        self,
        temporal: TemporalContext,
        *,
        past_days: int = 7,
        max_events: int = 15,
        max_past_events: int = 30,
    ) -> tuple[str, tuple[CalendarEvent, ...]]:
        """(bloco de texto, eventos usados). Deltas calculados pelo servidor.

        Inclui todos os eventos futuros (até `max_events`) e um histórico
        compacto dos passados (até `max_past_events`, os mais recentes) — o
        histórico permite responder "quando foi o AT?" e "o que aconteceu
        ontem?" sem RAG. `past_days` é mantido por compatibilidade de
        assinatura, mas o histórico não se limita mais a essa janela.
        """
        del past_days
        today = temporal.today
        # Cap 0 deve produzir lista vazia (em Python `seq[-0:]` == `seq[0:]`).
        if max_past_events > 0:
            past = [e for e in self.events if e.date < today][-max_past_events:]
        else:
            past = []
        future = (
            list(self.upcoming(today, limit=max_events)) if max_events > 0 else []
        )
        used = tuple(past + future)

        header = "## Agenda acadêmica (dados oficiais do sistema)"
        rules = (
            "Regras de uso da agenda:\n"
            "- As datas e contagens de dias acima foram calculadas pelo servidor "
            "com base na data de hoje — use-as como estão, sem recalcular.\n"
            "- Se perguntarem por um evento, prova, avaliação ou entrega que NÃO "
            "está listado aqui nem nos trechos [Fonte: …], declare que não há "
            "registo oficial — NÃO invente datas, professores, avaliações, "
            "horários nem prazos.\n"
            "- Se o histórico da conversa mencionar uma data diferente desta "
            "agenda, a agenda oficial tem prioridade; aponte a divergência ao "
            "responder."
        )

        if not used:
            body = (
                "Não há eventos acadêmicos registados no sistema neste momento. "
                "Se perguntarem sobre provas, avaliações, entregas ou eventos, "
                "declare que não há registo oficial e sugira confirmar com o "
                "responsável pela turma — NÃO invente datas nem prazos."
            )
            return f"{header}\n\n{body}", ()

        lines: list[str] = []
        if future:
            lines.append("Próximos eventos registados:")
            lines.extend(self._event_line(e, today) for e in future)
        else:
            lines.append(
                "Não há eventos FUTUROS registados no momento. Se perguntarem "
                "pela próxima prova/avaliação/entrega, declare que ainda não há "
                "registo oficial — NÃO invente datas."
            )
        if past:
            lines.append("")
            lines.append("Eventos passados registados (histórico):")
            lines.extend(self._event_line(e, today) for e in past)

        return f"{header}\n\n" + "\n".join(lines) + f"\n\n{rules}", used

    @staticmethod
    def _event_line(event: CalendarEvent, today: date) -> str:
        label = event_type_label(event.type)
        when = f"{weekday_name_pt(event.date)}, {event.date.isoformat()}"
        if event.time:
            when += f" às {event.time}"
        disc = f" ({event.discipline})" if event.discipline else ""
        delta = _delta_text(event.days_from(today))
        desc = f" — {event.description}" if event.description else ""
        return f"- [{label}] {event.title}{disc} — {when} — {delta}{desc}"


def _discipline_matches(event: CalendarEvent, discipline: str) -> bool:
    if not event.discipline:
        return False
    return discipline.strip().lower() in event.discipline.strip().lower() or (
        event.discipline.strip().lower() in discipline.strip().lower()
    )


def today_summary_pt(temporal: TemporalContext) -> str:
    """Resumo de 'hoje' para respostas factuais — calculado pelo backend."""
    return f"{format_date_pt(temporal.today)} ({temporal.date_iso})"
