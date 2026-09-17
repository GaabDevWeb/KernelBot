"""Registo de TP/AT — dados em `tps-assessments-infnet/` (branch true-kernel)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from kernel.academic.assessment_loader import load_assessment_entries
from kernel.academic.models import AssessmentEntry

log = logging.getLogger(f"kernelbots.{__name__}")

_DEFAULT_ASSESSMENTS_DIR = "tps-assessments-infnet"


@dataclass
class AssessmentCatalog:
    """Catálogo de avaliações (TP/AT/Assessment/Entrega)."""

    entries: tuple[AssessmentEntry, ...] = field(default_factory=tuple)

    def resolve(
        self,
        discipline: str,
        *,
        kind: str,
        number: int | None = None,
        slug: str | None = None,
    ) -> AssessmentEntry | None:
        disc = discipline.strip().lower()
        kind_l = kind.strip().lower()
        # AT sem número → assessment final (padrão INFNET: ficheiro assessment.md).
        if kind_l == "at" and number is None:
            kind_l = "assessment"
        for entry in self.entries:
            if entry.discipline != disc:
                continue
            if entry.kind != kind_l:
                continue
            if number is not None and entry.number == number:
                return entry
            if number is None and entry.number is None and slug and entry.slug == slug:
                return entry
            if number is None and entry.number is None and slug is None:
                # assessment/entrega: único por disciplina+kind
                if kind_l in ("assessment", "entrega"):
                    return entry
        return None

    def list_for_discipline(self, discipline: str) -> tuple[AssessmentEntry, ...]:
        disc = discipline.strip().lower()
        return tuple(e for e in self.entries if e.discipline == disc)

    @classmethod
    def empty(cls) -> AssessmentCatalog:
        log.info("AssessmentCatalog: vazio (pasta %s ausente ou sem ficheiros)", _DEFAULT_ASSESSMENTS_DIR)
        return cls()

    @classmethod
    def load(cls, project_root: Path) -> AssessmentCatalog:
        root = project_root / _DEFAULT_ASSESSMENTS_DIR
        entries = load_assessment_entries(root)
        if not entries:
            return cls.empty()
        return cls(entries=entries)
