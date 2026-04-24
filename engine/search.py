"""Índice BM25 por silo (disciplina) — fonte única: MySQL."""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any

from rank_bm25 import BM25Okapi

from core.config import GlobalContextMode
from core.config import Settings
from engine.database import fetch_db_chunks, fetch_db_discipline_ids

log = logging.getLogger(f"kernelbots.{__name__}")

_SAFE_DISCIPLINE_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class SearchEngine:
    """Tokeniza chunks do MySQL por silo, rebuild e busca com threshold normalizado."""

    def __init__(
        self,
        score_threshold: float,
        global_context_mode: GlobalContextMode = "geral",
        settings: Settings | None = None,
    ) -> None:
        self._score_threshold = score_threshold
        self._global_context_mode: GlobalContextMode = global_context_mode
        self._settings = settings
        self._lock = threading.RLock()
        self._silos: dict[str, dict[str, Any]] = {}
        self._discipline_ids: frozenset[str] = frozenset()
        self._all_chunks: list[dict] = []
        self.rebuild()

    @property
    def chunks(self) -> list[dict]:
        """Todos os chunks (união dos silos), útil para /doc e testes."""
        with self._lock:
            return list(self._all_chunks)

    @property
    def discipline_ids(self) -> frozenset[str]:
        with self._lock:
            return self._discipline_ids

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def rebuild(self) -> None:
        t0 = time.perf_counter()

        db_chunks: list[dict] = []
        if self._settings is not None:
            db_chunks = fetch_db_chunks(self._settings)

        if not db_chunks:
            log.warning(
                "⚠  Nenhum chunk carregado do MySQL — BM25 desativado. Modo assistente geral ativo."
            )

        chunks_by_silo: dict[str, list[dict]] = {}
        for chunk in db_chunks:
            silo = chunk.get("discipline", "geral")
            chunks_by_silo.setdefault(silo, []).append(chunk)

        new_silos: dict[str, dict[str, Any]] = {}
        all_chunks: list[dict] = []

        for silo in sorted(chunks_by_silo):
            silo_chunks = chunks_by_silo[silo]
            tokenized = [self._tokenize(c["text"]) for c in silo_chunks]
            bm25 = BM25Okapi(tokenized) if tokenized else None
            new_silos[silo] = {"chunks": silo_chunks, "bm25": bm25}
            all_chunks.extend(silo_chunks)
            log.info("   🗄  [%s] %s chunk(s) do MySQL", silo, len(silo_chunks))

        discipline_ids: frozenset[str] = frozenset()
        if self._settings is not None:
            discipline_ids = fetch_db_discipline_ids(self._settings)
        if not discipline_ids:
            discipline_ids = frozenset(chunks_by_silo.keys())

        elapsed = (time.perf_counter() - t0) * 1000
        with self._lock:
            self._discipline_ids = discipline_ids
            self._silos = new_silos
            self._all_chunks = all_chunks

        log.info(
            "✅ Índice BM25 por silo pronto — %s chunk(s) (MySQL) | %s silo(s) | rebuild em %.1fms",
            len(all_chunks), len(new_silos), elapsed,
        )

    def normalize_discipline(self, raw: str | None) -> str | None:
        """Whitelist contra disciplines reais; rejeita path traversal e caracteres inseguros."""
        if raw is None:
            return None
        s = raw.strip()
        if not s:
            return None
        if not _SAFE_DISCIPLINE_RE.match(s):
            log.warning("normalize_discipline: rejeitado (formato inseguro): %r", raw)
            return None
        with self._lock:
            known = self._discipline_ids
        if s not in known:
            log.warning("normalize_discipline: disciplina desconhecida (ignorada): %r", raw)
            return None
        return s

    def chunks_for_scope(self, discipline_filter: str | None) -> list[dict]:
        """Chunks do mesmo universo que uma busca sem hits (fallback /content)."""
        with self._lock:
            nd = self.normalize_discipline(discipline_filter)
            if nd is not None:
                return list(self._silos.get(nd, {}).get("chunks", []))
            if self._global_context_mode == "geral":
                merged: list[dict] = []
                for name in sorted(self._silos.keys()):
                    merged.extend(self._silos[name]["chunks"])
                return merged
            ordered: list[dict] = []
            for name in sorted(self._silos.keys()):
                ordered.extend(self._silos[name]["chunks"])
            return ordered

    def _hits_in_silo(self, silo: str, query: str, top_k: int) -> list[dict]:
        data = self._silos.get(silo)
        if not data or not data["bm25"] or not data["chunks"]:
            return []
        tokens = self._tokenize(query)
        scores = data["bm25"].get_scores(tokens)
        max_score = float(scores.max()) if len(scores) else 0.0
        if max_score == 0:
            return []
        norm = scores / max_score
        ranked = sorted(enumerate(norm), key=lambda x: x[1], reverse=True)
        out: list[dict] = []
        for i, s in ranked[:top_k]:
            if s >= self._score_threshold:
                out.append({**data["chunks"][i], "score": float(s)})
        return out

    def search(
        self,
        query: str,
        top_k: int = 3,
        discipline_filter: str | None = None,
    ) -> list[dict]:
        with self._lock:
            nd = self.normalize_discipline(discipline_filter)

            if nd is not None:
                return self._hits_in_silo(nd, query, top_k)

            if self._global_context_mode == "geral":
                merged: list[dict] = []
                for silo in sorted(self._silos.keys()):
                    merged.extend(self._hits_in_silo(silo, query, top_k))
                merged.sort(key=lambda h: h["score"], reverse=True)
                return merged[:top_k]

            merged_all: list[dict] = []
            for silo in sorted(self._silos.keys()):
                merged_all.extend(self._hits_in_silo(silo, query, top_k))
            merged_all.sort(key=lambda h: h["score"], reverse=True)
            return merged_all[:top_k]
