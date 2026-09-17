"""Catálogo do Manual do Aluno — guias Markdown com injecção selectiva no prompt."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(f"kernelbots.{__name__}")

_DEFAULT_MANIFEST = Path(__file__).resolve().parent / "data" / "student_manual_manifest.json"
_SKIP_FILES = frozenset({"readme.md", "_full_extract.txt"})


def _normalize(text: str) -> str:
    lowered = (text or "").strip().lower()
    decomposed = unicodedata.normalize("NFKD", lowered)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


@dataclass(frozen=True)
class ManualGuide:
    slug: str
    title: str
    content: str


@dataclass(frozen=True)
class StudentManualCatalog:
    """Guias oficiais do Manual do Aluno (INFNET) — injecção com budget."""

    title: str
    guides: dict[str, ManualGuide]
    default_course_slug: str
    always_on_slugs: tuple[str, ...]
    keyword_map: dict[str, tuple[str, ...]]
    discipline_course_slugs: dict[str, str]
    total_budget_chars: int = 14000
    always_on_max_chars: int = 2800
    matched_max_chars: int = 5000

    @classmethod
    def load(
        cls,
        guides_dir: Path | None,
        manifest_path: Path | None = None,
    ) -> StudentManualCatalog | None:
        manifest_path = manifest_path or _DEFAULT_MANIFEST
        if guides_dir is None or not guides_dir.is_dir():
            log.warning("StudentManualCatalog: pasta ausente %s", guides_dir)
            return None
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("StudentManualCatalog: manifest inválido %s: %s", manifest_path, exc)
            return None
        if not isinstance(raw, dict):
            return None

        guides: dict[str, ManualGuide] = {}
        for path in sorted(guides_dir.glob("*.md")):
            if path.name.lower() in _SKIP_FILES:
                continue
            slug = path.stem
            try:
                text = path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                log.warning("StudentManualCatalog: falha ao ler %s: %s", path, exc)
                continue
            if not text:
                continue
            title = _title_from_markdown(text) or slug.replace("-", " ").title()
            guides[slug] = ManualGuide(slug=slug, title=title, content=text)

        if not guides:
            log.warning("StudentManualCatalog: nenhum guia em %s", guides_dir)
            return None

        kw_raw = raw.get("keyword_map") or {}
        keyword_map: dict[str, tuple[str, ...]] = {}
        if isinstance(kw_raw, dict):
            for slug, terms in kw_raw.items():
                if isinstance(terms, list):
                    keyword_map[str(slug)] = tuple(str(t).strip().lower() for t in terms if str(t).strip())

        disc_raw = raw.get("discipline_course_slugs") or {}
        discipline_course_slugs = (
            {str(k): str(v) for k, v in disc_raw.items()} if isinstance(disc_raw, dict) else {}
        )

        always_on = tuple(str(s) for s in (raw.get("always_on_slugs") or []) if str(s) in guides)

        catalog = cls(
            title=str(raw.get("title") or "Manual do Aluno").strip(),
            guides=guides,
            default_course_slug=str(
                raw.get("default_course_slug") or "analise-e-desenvolvimento-de-sistemas"
            ),
            always_on_slugs=always_on,
            keyword_map=keyword_map,
            discipline_course_slugs=discipline_course_slugs,
            total_budget_chars=int(raw.get("total_budget_chars") or 14000),
            always_on_max_chars=int(raw.get("always_on_max_chars") or 2800),
            matched_max_chars=int(raw.get("matched_max_chars") or 5000),
        )
        log.info(
            "StudentManualCatalog: %d guias carregados de %s",
            len(guides),
            guides_dir,
        )
        return catalog

    def _truncate(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."

    def _match_slugs(
        self,
        query: str,
        *,
        discipline_id: str | None,
        recent_queries: tuple[str, ...] | None,
    ) -> list[str]:
        combined = _normalize(" ".join([*(recent_queries or ()), query or ""]))
        matched: list[tuple[int, str]] = []
        for slug, terms in self.keyword_map.items():
            if slug not in self.guides:
                continue
            score = 0
            for term in terms:
                nt = _normalize(term)
                if nt and nt in combined:
                    score += max(1, len(nt) // 4)
            if score:
                matched.append((score, slug))
        matched.sort(key=lambda x: (-x[0], x[1]))

        course_slug = self.default_course_slug
        if discipline_id and discipline_id in self.discipline_course_slugs:
            course_slug = self.discipline_course_slugs[discipline_id]
        if course_slug in self.guides:
            matched.append((1000, course_slug))

        out: list[str] = []
        seen: set[str] = set()
        for _score, slug in matched:
            if slug in seen:
                continue
            seen.add(slug)
            out.append(slug)
        return out

    def prompt_section(
        self,
        query: str = "",
        *,
        discipline_id: str | None = None,
        recent_queries: tuple[str, ...] | None = None,
    ) -> str:
        if not self.guides:
            return ""

        selected_slugs: list[str] = []
        for slug in self.always_on_slugs:
            if slug in self.guides and slug not in selected_slugs:
                selected_slugs.append(slug)
        for slug in self._match_slugs(
            query, discipline_id=discipline_id, recent_queries=recent_queries
        ):
            if slug not in selected_slugs:
                selected_slugs.append(slug)

        lines = [
            f"## {self.title}",
            "Fonte oficial institucional (Manual do Aluno INFNET). "
            "Priorize estes dados sobre conhecimento genérico para regras, prazos, "
            "presença, TPs/ATs, IA, sistemas e organização curricular.",
            "Não invente políticas — se não constar aqui, diga que não há registo.",
        ]

        used = 0
        index_parts: list[str] = []
        for slug in sorted(self.guides):
            index_parts.append(f"- {self.guides[slug].title} (`{slug}`)")
        lines.append("\n### Índice de guias disponíveis\n" + "\n".join(index_parts[:40]))

        for slug in selected_slugs:
            guide = self.guides.get(slug)
            if guide is None:
                continue
            cap = (
                self.always_on_max_chars
                if slug in self.always_on_slugs
                else self.matched_max_chars
            )
            remaining = self.total_budget_chars - used
            if remaining <= 500:
                break
            cap = min(cap, remaining)
            body = self._truncate(guide.content, cap)
            used += len(body)
            tag = "núcleo" if slug in self.always_on_slugs else "relevante à pergunta"
            lines.append(f"\n### Guia: {guide.title} ({tag})\n\n{body}")

        return "\n".join(lines)


def _title_from_markdown(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return None
