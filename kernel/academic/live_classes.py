"""Links das aulas ao vivo por disciplina (Zoom INFNET)."""

from __future__ import annotations

import json
import logging
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from kernel.context.temporal import TemporalContext, format_date_pt

log = logging.getLogger(f"kernelbots.{__name__}")


@dataclass(frozen=True)
class LiveClassSession:
    discipline_id: str
    label: str
    weekday: str
    time: str
    zoom_url: str


@dataclass(frozen=True)
class LiveClassSemester:
    id: int
    label: str
    sessions: tuple[LiveClassSession, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class LiveClassesCatalog:
    """Horário e links Zoom das aulas síncronas."""

    title: str = "Links das aulas ao vivo (Zoom INFNET)"
    semesters: tuple[LiveClassSemester, ...] = field(default_factory=tuple)

    @classmethod
    def load(cls, path: Path | None) -> LiveClassesCatalog | None:
        if path is None or not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("LiveClassesCatalog: falha ao ler %s: %s", path, exc)
            return None
        if not isinstance(raw, dict):
            return None
        semesters_out: list[LiveClassSemester] = []
        for sem_raw in raw.get("semesters") or []:
            if not isinstance(sem_raw, dict):
                continue
            sessions_out: list[LiveClassSession] = []
            for sess in sem_raw.get("sessions") or []:
                if not isinstance(sess, dict):
                    continue
                url = str(sess.get("zoom_url") or "").strip()
                disc = str(sess.get("discipline_id") or "").strip().lower()
                if not url or not disc:
                    continue
                sessions_out.append(
                    LiveClassSession(
                        discipline_id=disc,
                        label=str(sess.get("label") or disc).strip(),
                        weekday=str(sess.get("weekday") or "").strip(),
                        time=str(sess.get("time") or "").strip(),
                        zoom_url=url,
                    )
                )
            if sessions_out:
                semesters_out.append(
                    LiveClassSemester(
                        id=int(sem_raw.get("id") or len(semesters_out) + 1),
                        label=str(sem_raw.get("label") or f"Semestre {len(semesters_out) + 1}").strip(),
                        sessions=tuple(sessions_out),
                    )
                )
        if not semesters_out:
            return None
        return cls(
            title=str(raw.get("title") or cls.title).strip(),
            semesters=tuple(semesters_out),
        )

    def sessions_for_discipline(self, discipline_id: str) -> tuple[LiveClassSession, ...]:
        disc = discipline_id.strip().lower()
        out: list[LiveClassSession] = []
        for sem in self.semesters:
            for sess in sem.sessions:
                if sess.discipline_id == disc:
                    out.append(sess)
        return tuple(out)

    @staticmethod
    def _normalize_weekday(name: str) -> str:
        lowered = (name or "").strip().lower()
        decomposed = unicodedata.normalize("NFKD", lowered)
        plain = "".join(c for c in decomposed if not unicodedata.combining(c))
        return plain.replace("terca", "terça").replace("sabado", "sábado")

    def sessions_on_weekday(self, weekday: str) -> tuple[tuple[str, LiveClassSession], ...]:
        wd = self._normalize_weekday(weekday)
        out: list[tuple[str, LiveClassSession]] = []
        for sem in self.semesters:
            for sess in sem.sessions:
                if self._normalize_weekday(sess.weekday) == wd:
                    out.append((sem.label, sess))
        return tuple(out)

    def today_prompt_section(self, temporal: TemporalContext) -> str:
        """Secção determinística para 'hoje tem aula?' — horário recorrente Zoom."""
        wd = temporal.weekday_name
        sessions = self.sessions_on_weekday(wd)
        lines = [
            "### Hoje — aulas síncronas (horário semanal recorrente)",
            f"Data: {format_date_pt(temporal.today)} ({temporal.date_iso})",
        ]
        if not sessions:
            lines.append(
                f"Não há aula síncrona recorrente agendada para **{wd}** no horário semanal da turma."
            )
        else:
            lines.append(
                "Para \"hoje tem aula?\" / \"qual o link da aula hoje?\", estas sessões Zoom "
                "**contam como aula síncrona agendada** (grade semanal fixa), mesmo que a agenda "
                "de eventos acima não liste nada para esta data:"
            )
            for sem_label, sess in sessions:
                lines.append(
                    f"- [{sem_label}] {sess.time} — {sess.label} (Zoom): {sess.zoom_url}"
                )
        return "\n".join(lines)

    def prompt_section(self, discipline_id: str | None = None) -> str:
        if not self.semesters:
            return ""
        lines = [
            f"## {self.title}",
            "Use estes links oficiais quando o aluno pedir aula ao vivo, Zoom ou horário síncrono.",
            "Não invente URLs — só as listadas abaixo.",
        ]
        focus = discipline_id.strip().lower() if discipline_id else None
        if focus:
            matched = self.sessions_for_discipline(focus)
            if matched:
                lines.append(f"\n### Destaque — disciplina activa (`{focus}`)")
                for sess in matched:
                    lines.append(
                        f"- {sess.weekday} ({sess.time}) — {sess.label}: {sess.zoom_url}"
                    )
        for sem in self.semesters:
            lines.append(f"\n### {sem.label}")
            for sess in sem.sessions:
                lines.append(
                    f"- {sess.weekday} ({sess.time}) — {sess.label}: {sess.zoom_url}"
                )
        return "\n".join(lines)
