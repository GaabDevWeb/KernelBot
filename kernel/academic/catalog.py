"""Catálogo académico ordenado — consultas determinísticas sobre aulas."""

from __future__ import annotations

import logging
from collections import defaultdict

from kernel.academic.models import AcademicDiscipline, AcademicLesson
from kernel.disciplines.disciplines import discipline_by_id, trace_label_by_discipline
from kernel.knowledge.iss_links import iss_lesson_url
from kernel.knowledge.lesson_catalog import normalize_lesson_key

log = logging.getLogger(f"kernelbots.{__name__}")


class AcademicCatalog:
    """Mapa académico: disciplinas → aulas ordenadas por `order`."""

    def __init__(
        self,
        lessons: list[AcademicLesson],
        *,
        iss_base: str,
        source: str,
    ) -> None:
        self._iss_base = iss_base
        self._source = source
        by_disc: dict[str, list[AcademicLesson]] = defaultdict(list)
        for lesson in lessons:
            by_disc[lesson.discipline].append(lesson)
        self._by_disc: dict[str, tuple[AcademicLesson, ...]] = {}
        for disc, rows in by_disc.items():
            ordered = tuple(sorted(rows, key=lambda l: (l.order, l.slug)))
            self._by_disc[disc] = ordered
        self._by_key: dict[str, AcademicLesson] = {
            normalize_lesson_key(l.discipline, l.slug): l for l in lessons
        }

    @property
    def source(self) -> str:
        return self._source

    @classmethod
    def from_rows(
        cls,
        rows: list[dict],
        *,
        iss_base: str,
        source: str = "mysql",
    ) -> AcademicCatalog | None:
        lessons: list[AcademicLesson] = []
        for row in rows:
            disc = str(row.get("discipline") or "").strip().lower()
            slug = str(row.get("slug") or "").strip().lower()
            if not disc or not slug:
                continue
            title = str(row.get("title") or slug).strip()
            order = int(row.get("order") or 0)
            if order <= 0:
                continue
            source_id = str(row.get("source") or f"db:{disc}/{slug}")
            url = iss_lesson_url(disc, slug, iss_base)
            lessons.append(
                AcademicLesson(
                    discipline=disc,
                    slug=slug,
                    title=title,
                    order=order,
                    source=source_id,
                    url=url,
                )
            )
        if not lessons:
            return None
        log.info("AcademicCatalog carregado (%s): %d aulas", source, len(lessons))
        return cls(lessons, iss_base=iss_base, source=source)

    def discipline_ids(self) -> list[str]:
        return sorted(self._by_disc.keys())

    def lessons_for_discipline(self, discipline_id: str) -> tuple[AcademicLesson, ...]:
        disc = discipline_id.strip().lower()
        return self._by_disc.get(disc, ())

    def lesson_by_key(self, discipline: str, slug: str) -> AcademicLesson | None:
        return self._by_key.get(normalize_lesson_key(discipline, slug))

    def lesson_by_order(self, discipline: str, order: int) -> AcademicLesson | None:
        if order <= 0:
            return None
        for lesson in self.lessons_for_discipline(discipline):
            if lesson.order == order:
                return lesson
        return None

    def first_lesson(self, discipline: str) -> AcademicLesson | None:
        lessons = self.lessons_for_discipline(discipline)
        return lessons[0] if lessons else None

    def last_lesson(self, discipline: str) -> AcademicLesson | None:
        lessons = self.lessons_for_discipline(discipline)
        return lessons[-1] if lessons else None

    def adjacent_lesson(
        self,
        discipline: str,
        *,
        slug: str | None = None,
        order: int | None = None,
        direction: str,
    ) -> AcademicLesson | None:
        lessons = self.lessons_for_discipline(discipline)
        if not lessons:
            return None
        idx: int | None = None
        if order is not None:
            for i, lesson in enumerate(lessons):
                if lesson.order == order:
                    idx = i
                    break
        elif slug:
            key = normalize_lesson_key(discipline, slug)
            for i, lesson in enumerate(lessons):
                if normalize_lesson_key(lesson.discipline, lesson.slug) == key:
                    idx = i
                    break
        if idx is None:
            return None
        if direction == "previous":
            return lessons[idx - 1] if idx > 0 else None
        if direction == "next":
            return lessons[idx + 1] if idx + 1 < len(lessons) else None
        return None

    def discipline_summary(self, discipline_id: str) -> AcademicDiscipline | None:
        lessons = self.lessons_for_discipline(discipline_id)
        if not lessons:
            return None
        cfg = discipline_by_id(discipline_id)
        labels = trace_label_by_discipline()
        label = cfg.label if cfg else labels.get(discipline_id, discipline_id)
        return AcademicDiscipline(
            id=discipline_id,
            label=label,
            lesson_count=len(lessons),
            lessons=lessons,
        )

    def build_map_prompt_section(self, discipline_id: str | None = None) -> str:
        """Mapa académico compacto para o prompt (Manual do Aluno — camada estrutural)."""
        if discipline_id:
            summary = self.discipline_summary(discipline_id)
            if summary is None:
                return ""
            lines = [
                f"## Mapa académico — {summary.label} (`{summary.id}`)",
                f"- Total de aulas indexadas: {summary.lesson_count}",
                "- Sequência (ordem canónica):",
            ]
            for lesson in summary.lessons:
                lines.append(
                    f"  - Aula {lesson.order}: **{lesson.title}** "
                    f"(`{lesson.slug}`)"
                )
            return "\n".join(lines)

        lines = ["## Mapa académico — disciplinas indexadas"]
        for disc in self.discipline_ids():
            count = len(self.lessons_for_discipline(disc))
            label = trace_label_by_discipline().get(disc, disc)
            lines.append(f"- **{label}** (`{disc}`): {count} aulas")
        return "\n".join(lines)
