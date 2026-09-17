"""Bootstrap do estado académico (catálogo + manual + avaliações)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kernel.academic.assessment_catalog import AssessmentCatalog
from kernel.academic.catalog import AcademicCatalog
from kernel.academic.live_classes import LiveClassesCatalog
from kernel.academic.loader import load_academic_catalog
from kernel.academic.student_manual_catalog import StudentManualCatalog
from kernel.config import Settings


@dataclass(frozen=True)
class AcademicState:
    catalog: AcademicCatalog | None
    assessment_catalog: AssessmentCatalog
    student_manual: StudentManualCatalog | None
    live_classes: LiveClassesCatalog | None


def bootstrap_academic_state(settings: Settings) -> AcademicState:
    live_path: Path = settings.context_dir / "live_classes.json"
    if not live_path.is_file():
        live_path = settings.project_root / "kernel" / "academic" / "data" / "live_classes.json"
    manual_dir = settings.project_root / "manual do aluno"
    if not manual_dir.is_dir():
        manual_dir = settings.context_dir / "manual do aluno"
    return AcademicState(
        catalog=load_academic_catalog(settings),
        assessment_catalog=AssessmentCatalog.load(settings.project_root),
        student_manual=StudentManualCatalog.load(manual_dir if manual_dir.is_dir() else None),
        live_classes=LiveClassesCatalog.load(live_path if live_path.is_file() else None),
    )
