"""Manual do Aluno — camada de mapa académico (não dump de conteúdo)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(f"kernelbots.{__name__}")


@dataclass(frozen=True)
class StudentManual:
    """Metadados estruturais opcionais além do catálogo automático."""

    title: str = "Manual do Aluno"
    notes: tuple[str, ...] = field(default_factory=tuple)
    discipline_notes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None) -> StudentManual | None:
        if path is None or not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("StudentManual: falha ao ler %s: %s", path, exc)
            return None
        if not isinstance(raw, dict):
            return None
        notes_raw = raw.get("notes") or []
        notes = tuple(str(n).strip() for n in notes_raw if str(n).strip())
        disc_notes = raw.get("discipline_notes") or {}
        if not isinstance(disc_notes, dict):
            disc_notes = {}
        return cls(
            title=str(raw.get("title") or "Manual do Aluno").strip(),
            notes=notes,
            discipline_notes={str(k): str(v) for k, v in disc_notes.items()},
        )

    def prompt_section(self, discipline_id: str | None = None) -> str:
        lines = [f"## {self.title}"]
        if discipline_id and discipline_id in self.discipline_notes:
            lines.append(self.discipline_notes[discipline_id])
        for note in self.notes:
            lines.append(f"- {note}")
        body = "\n".join(lines).strip()
        return body if len(body) > len(self.title) + 4 else ""
