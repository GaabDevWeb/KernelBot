"""Catálogo lexical de aulas (ISS JSON) — Fase 0.

Roteamento sem LLM: BM25 simplificado sobre título + resumo por aula.
Chaves `discipline:slug` normalizadas via `normalize_lesson_key` para
alinhar catálogo, índice MySQL e filtros de retrieval.

Regra de normalização (sem remoção de acentos): strip, lower, `_` → `-`.
"""

from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from core.config import Settings

log = logging.getLogger(f"kernelbots.{__name__}")

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

_BM25_K1 = 1.5
_BM25_B = 0.75


def _normalize_part(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def normalize_lesson_key(discipline: str, slug: str) -> str:
    """Chave canônica `discipline:slug` — única função para catálogo, DB e drift."""
    return f"{_normalize_part(discipline)}:{_normalize_part(slug)}"


@dataclass(frozen=True)
class LessonEntry:
    discipline: str
    slug: str
    title: str
    name: str
    lesson_id: str | None = None
    excerpt: str | None = None


@dataclass(frozen=True)
class CatalogMatch:
    lesson: LessonEntry
    score: float


@dataclass
class CatalogMatchResult:
    matches: list[CatalogMatch]

    @property
    def top_score(self) -> float:
        return self.matches[0].score if self.matches else 0.0

    @property
    def second_score(self) -> float:
        return self.matches[1].score if len(self.matches) > 1 else 0.0

    @property
    def margin(self) -> float:
        return self.top_score - self.second_score


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _display_name(title: str, slug: str) -> str:
    t = (title or "").strip()
    if t:
        return t
    return slug.replace("-", " ").strip() or slug


class _IndexedLesson:
    __slots__ = ("entry", "tokens")

    def __init__(self, entry: LessonEntry, tokens: list[str]) -> None:
        self.entry = entry
        self.tokens = tokens


class _CorpusStats:
    def __init__(self, docs: list[list[str]]) -> None:
        self.n_docs = max(1, len(docs))
        self.avgdl = sum(len(d) for d in docs) / self.n_docs if docs else 1.0
        self.df: Counter[str] = Counter()
        for tokens in docs:
            for term in set(tokens):
                self.df[term] += 1

    def idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log((self.n_docs - df + 0.5) / (df + 0.5) + 1.0)


def _bm25_score(query_tokens: list[str], doc_tokens: list[str], stats: _CorpusStats) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    tf_map = Counter(doc_tokens)
    doc_len = len(doc_tokens)
    score = 0.0
    for term in set(query_tokens):
        freq = tf_map.get(term, 0)
        if freq <= 0:
            continue
        idf = stats.idf(term)
        denom = freq + _BM25_K1 * (1.0 - _BM25_B + _BM25_B * doc_len / stats.avgdl)
        score += idf * (freq * (_BM25_K1 + 1.0)) / denom
    return score


def _lesson_document_text(entry: LessonEntry) -> str:
    parts = [entry.title, entry.name, entry.slug.replace("-", " ")]
    if entry.excerpt:
        parts.append(entry.excerpt)
    return " ".join(p for p in parts if p)


def _parse_db_source_key(source: str) -> str | None:
    if not source.startswith("db:"):
        return None
    rest = source[3:]
    if "/" not in rest:
        return None
    disc, slug_part = rest.split("/", 1)
    slug = slug_part.split("/", 1)[0]
    return normalize_lesson_key(disc, slug)


class LessonCatalog:
    """Catálogo em memória com ranking lexical e gates de confiança."""

    def __init__(
        self,
        lessons: list[_IndexedLesson],
        stats: _CorpusStats,
        *,
        min_score: float,
        min_margin: float,
        strict_threshold: float,
        prompt_top_k: int,
    ) -> None:
        self._lessons = lessons
        self._stats = stats
        self._min_score = min_score
        self._min_margin = min_margin
        self._strict_threshold = strict_threshold
        self._prompt_top_k = max(1, prompt_top_k)
        self._keys: frozenset[str] = frozenset(
            normalize_lesson_key(il.entry.discipline, il.entry.slug) for il in lessons
        )

    @classmethod
    def load(cls, settings: Settings) -> LessonCatalog | None:
        if not settings.catalog_enabled:
            return None
        base = settings.catalog_json_dir
        if base is None or not base.is_dir():
            log.warning(
                "Catálogo habilitado mas ACL_CATALOG_JSON_DIR inválido ou ausente: %s",
                base,
            )
            return None

        lessons_path = base / "lessons.json"
        index_path = base / "search-index.json"
        if not lessons_path.is_file():
            log.warning("lessons.json não encontrado em %s", base)
            return None

        try:
            raw_lessons = json.loads(lessons_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Falha ao ler lessons.json: %s", exc)
            return None

        excerpts: dict[tuple[str, str], str] = {}
        if index_path.is_file():
            try:
                raw_index = json.loads(index_path.read_text(encoding="utf-8"))
                for row in raw_index:
                    if not isinstance(row, dict):
                        continue
                    disc_raw = str(row.get("discipline") or "")
                    slug_raw = str(row.get("slug") or "")
                    if not disc_raw or not slug_raw:
                        continue
                    if "exemplo" in disc_raw.lower() or "exemplo" in slug_raw.lower():
                        continue
                    key = normalize_lesson_key(disc_raw, slug_raw)
                    excerpt = str(row.get("excerpt") or "").strip()
                    if excerpt:
                        excerpts[key] = excerpt
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("Falha ao ler search-index.json (continuando sem excerpts): %s", exc)

        indexed: list[_IndexedLesson] = []
        for row in raw_lessons:
            if not isinstance(row, dict):
                continue
            disc_raw = str(row.get("discipline") or "").strip()
            slug_raw = str(row.get("slug") or "").strip()
            if not disc_raw or not slug_raw:
                continue
            key = normalize_lesson_key(disc_raw, slug_raw)
            disc, slug = key.split(":", 1)
            title = str(row.get("title") or "").strip()
            name = _display_name(title, slug)
            lesson_id = row.get("lesson_id")
            if lesson_id is not None:
                lesson_id = str(lesson_id)
            entry = LessonEntry(
                discipline=disc,
                slug=slug,
                title=title or name,
                name=name,
                lesson_id=lesson_id,
                excerpt=excerpts.get(key),
            )
            tokens = _tokenize(_lesson_document_text(entry))
            if tokens:
                indexed.append(_IndexedLesson(entry, tokens))

        if not indexed:
            log.warning("Catálogo sem aulas indexáveis em %s", base)
            return None

        stats = _CorpusStats([il.tokens for il in indexed])
        log.info(
            "LessonCatalog carregado: %d aulas de %s",
            len(indexed),
            base,
        )
        return cls(
            indexed,
            stats,
            min_score=settings.catalog_min_score,
            min_margin=settings.catalog_min_margin,
            strict_threshold=settings.catalog_strict_threshold,
            prompt_top_k=settings.catalog_prompt_top_k,
        )

    def lesson_key(self, lesson: LessonEntry) -> str:
        return normalize_lesson_key(lesson.discipline, lesson.slug)

    def match(self, query: str) -> CatalogMatchResult:
        tokens = _tokenize(query)
        if not tokens:
            return CatalogMatchResult(matches=[])

        scored: list[CatalogMatch] = []
        for il in self._lessons:
            score = _bm25_score(tokens, il.tokens, self._stats)
            if score > 0:
                scored.append(CatalogMatch(lesson=il.entry, score=score))

        scored.sort(key=lambda m: m.score, reverse=True)
        top = scored[: self._prompt_top_k]
        return CatalogMatchResult(matches=top)

    def is_confident(self, result: CatalogMatchResult) -> bool:
        if not result.matches:
            return False
        return (
            result.top_score >= self._min_score
            and result.margin >= self._min_margin
        )

    def is_strict_confident(self, result: CatalogMatchResult) -> bool:
        """Gate mais alto para pré-escopo BM25 (Fase futura); exige margem também."""
        if not result.matches:
            return False
        return (
            result.top_score >= self._strict_threshold
            and result.margin >= self._min_margin
        )

    def is_operational_confident(
        self,
        result: CatalogMatchResult,
        indexed_keys: frozenset[str],
    ) -> bool:
        lesson = self.top_lesson(result)
        if lesson is None:
            return False
        return self.is_confident(result) and self.lesson_key(lesson) in indexed_keys

    def top_lesson(self, result: CatalogMatchResult) -> LessonEntry | None:
        if not result.matches:
            return None
        return result.matches[0].lesson

    def filter_candidates_to_lesson(
        self,
        candidates: list,
        lesson: LessonEntry,
    ) -> list:
        target = self.lesson_key(lesson)
        out: list = []
        for cand in candidates:
            source = cand.source if hasattr(cand, "source") else cand.get("source", "")
            key = _parse_db_source_key(str(source))
            if key == target:
                out.append(cand)
        return out

    def build_prompt_section(self, result: CatalogMatchResult) -> str:
        lesson = self.top_lesson(result)
        if lesson is None:
            return ""
        lines = [
            "## Aula provável no catálogo",
            f"- **{lesson.name}**",
            f"- Disciplina: `{lesson.discipline}`",
            f"- Identificador: `{lesson.discipline}/{lesson.slug}`",
        ]
        if lesson.excerpt:
            excerpt = lesson.excerpt.strip()
            if len(excerpt) > 600:
                excerpt = excerpt[:600] + "…"
            lines.append(f"- Resumo do catálogo: {excerpt}")
        lines.append(
            "\nUse os trechos RAG abaixo como única base factual; "
            "o resumo acima serve só para orientar o escopo."
        )
        return "\n".join(lines)

    def audit_drift(
        self,
        indexed_keys: frozenset[str],
    ) -> dict:
        catalog_keys = self._keys
        catalog_only = sorted(catalog_keys - indexed_keys)
        index_only = sorted(indexed_keys - catalog_keys)
        return {
            "catalog_only": catalog_only,
            "index_only": index_only,
            "catalog_count": len(catalog_keys),
            "index_count": len(indexed_keys),
            "catalog_only_count": len(catalog_only),
            "index_only_count": len(index_only),
        }
