"""Índice BM25 por silo (disciplina) — fonte única: MySQL.

O `SearchEngine` é responsável apenas por **recuperação lexical bruta**.
A decisão de suficiência (hard stop, coverage, etc.) está em
`engine.retrieval.build_decision`. O plano
`rag_acl_incremental_6951b55f.plan.md` exige essa separação: retrieval
devolve candidatos com score cru e normalizado; a política fica fora.

Compatibilidade retroativa: `search()` continua disponível e devolve
`list[dict]`, mas agora NÃO aplica o threshold antigo de score — apenas
`top_k` e, opcionalmente, o gate de score absoluto. Código novo deve usar
`search_candidates()`.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any

from rank_bm25 import BM25Okapi

from core.config import GlobalContextMode
from core.config import Settings
from core.structured_log import ACL_MOD_SEARCH, log_event
from engine.database import fetch_db_chunks, fetch_db_discipline_ids
from engine.retrieval import CANDIDATE_K, RetrievalCandidate, expand_query_tokens

log = logging.getLogger(f"kernelbots.{__name__}")

_SAFE_DISCIPLINE_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _log_search_candidates(
    query: str,
    discipline_filter: str | None,
    cands: list[RetrievalCandidate],
    candidate_k: int,
) -> None:
    base_tokens = re.findall(r"\w+", query.lower())
    expanded = expand_query_tokens(base_tokens)
    top = cands[0].raw_score if cands else 0.0
    second = cands[1].raw_score if len(cands) > 1 else 0.0
    log_event(
        log,
        logging.INFO,
        ACL_MOD_SEARCH,
        "candidates_retrieved",
        "busca lexical concluida",
        metadata={
            "query": query,
            "normalized_query_tokens": expanded,
            "discipline_filter": discipline_filter,
            "candidate_k_requested": candidate_k,
            "candidate_count": len(cands),
            "top_score": top,
            "second_score": second,
            "score_margin": top - second,
            "top_sources": [c.source for c in cands[:10]],
            "top_raw_scores": [round(c.raw_score, 4) for c in cands[:10]],
        },
    )


class SearchEngine:
    """Tokeniza chunks do MySQL por silo, rebuild e busca com scores crus.

    Mudanças Fase 1:
    - `search_candidates()` devolve `RetrievalCandidate` com `raw_score`
      (BM25 puro) e `normalized_score` (normalizado por silo apenas para
      ranking local/UI).
    - `search()` permanece para compatibilidade mas não aplica mais o
      threshold antigo — a política de corte passa para `retrieval.py`.
    """

    def __init__(
        self,
        score_threshold: float,
        global_context_mode: GlobalContextMode = "geral",
        settings: Settings | None = None,
    ) -> None:
        self._score_threshold = score_threshold  # mantido para backward compat.
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
            log_event(
                log,
                logging.WARNING,
                ACL_MOD_SEARCH,
                "index_empty",
                "nenhum chunk MySQL — BM25 sem dados",
                metadata={"chunk_total": 0},
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
            log_event(
                log,
                logging.DEBUG,
                ACL_MOD_SEARCH,
                "silo_indexed",
                f"silo {silo} indexado",
                metadata={"silo": silo, "chunk_count": len(silo_chunks)},
            )

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

        log_event(
            log,
            logging.INFO,
            ACL_MOD_SEARCH,
            "index_rebuilt",
            "indice BM25 reconstruido",
            metadata={
                "chunk_total": len(all_chunks),
                "silo_count": len(new_silos),
                "silos": sorted(new_silos.keys()),
                "rebuild_ms": round(elapsed, 2),
            },
        )

    def normalize_discipline(self, raw: str | None) -> str | None:
        """Whitelist contra disciplines reais; rejeita path traversal e caracteres inseguros."""
        if raw is None:
            return None
        s = raw.strip()
        if not s:
            return None
        if not _SAFE_DISCIPLINE_RE.match(s):
            log_event(
                log,
                logging.WARNING,
                ACL_MOD_SEARCH,
                "discipline_rejected",
                "formato de disciplina inseguro",
                metadata={"raw": raw},
            )
            return None
        with self._lock:
            known = self._discipline_ids
        if s not in known:
            log_event(
                log,
                logging.WARNING,
                ACL_MOD_SEARCH,
                "discipline_unknown",
                "disciplina fora da whitelist",
                metadata={"raw": raw},
            )
            return None
        return s

    def chunks_for_scope(self, discipline_filter: str | None) -> list[dict]:
        """Chunks do mesmo universo que uma busca sem hits.

        Observação: o plano proíbe usar isso como fallback de resposta
        (ex.: `scope_chunks[:5]`). Continuamos expondo o método porque ele
        é útil para UI/debug, mas a camada de contexto não deve montar
        prompt com chunks não-retornados pela busca.
        """
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

    def _candidates_in_silo(
        self, silo: str, query: str, candidate_k: int,
    ) -> list[RetrievalCandidate]:
        data = self._silos.get(silo)
        if not data or not data["bm25"] or not data["chunks"]:
            return []
        tokens = self._tokenize(query)
        if not tokens:
            return []
        # Fase 3: expansão lexical conservadora (acento-sem-acento) para
        # tolerar queries mal acentuadas sem aumentar complexidade do
        # indexer. Só adiciona variantes, nunca remove.
        expanded = expand_query_tokens(tokens)
        raw = data["bm25"].get_scores(expanded)
        max_score = float(raw.max()) if len(raw) else 0.0
        if max_score == 0:
            return []
        ranked = sorted(enumerate(raw), key=lambda x: x[1], reverse=True)
        out: list[RetrievalCandidate] = []
        query_tokens = set(expanded)
        for i, s in ranked[: candidate_k]:
            raw_score = float(s)
            if raw_score <= 0:
                continue
            chunk = data["chunks"][i]
            chunk_tokens = self._tokenize(chunk["text"])
            matched = tuple(t for t in query_tokens if t in chunk_tokens)
            out.append(
                RetrievalCandidate(
                    source=str(chunk.get("source", "")),
                    chunk_id=f"{silo}:{i}",
                    text=str(chunk.get("text", "")),
                    discipline=str(chunk.get("discipline", silo)),
                    raw_score=raw_score,
                    normalized_score=raw_score / max_score,
                    matched_terms=matched,
                )
            )
        return out

    def search_candidates(
        self,
        query: str,
        candidate_k: int = CANDIDATE_K,
        discipline_filter: str | None = None,
    ) -> list[RetrievalCandidate]:
        """Retorna candidatos brutos ordenados por `raw_score` desc.

        Sem threshold, sem truncamento por top_k. A decisão fica com
        `engine.retrieval.build_decision`.
        """
        with self._lock:
            nd = self.normalize_discipline(discipline_filter)

            if nd is not None:
                cands = self._candidates_in_silo(nd, query, candidate_k)
                cands.sort(key=lambda c: c.raw_score, reverse=True)
                _log_search_candidates(query, nd, cands, candidate_k)
                return cands

            merged: list[RetrievalCandidate] = []
            for silo in sorted(self._silos.keys()):
                merged.extend(self._candidates_in_silo(silo, query, candidate_k))
            merged.sort(key=lambda c: c.raw_score, reverse=True)
            merged = merged[:candidate_k]
            _log_search_candidates(query, nd, merged, candidate_k)
            return merged

    # --- Compatibilidade retroativa -----------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 3,
        discipline_filter: str | None = None,
    ) -> list[dict]:
        """API antiga mantida para código legado.

        Hoje delega para `search_candidates()` e devolve dicts no formato
        antigo, mas com `score` = `normalized_score` (mantém semântica da
        UI). Código novo deve consumir `search_candidates()`.
        """
        cands = self.search_candidates(query, candidate_k=top_k, discipline_filter=discipline_filter)
        return [
            {
                "source": c.source,
                "text": c.text,
                "discipline": c.discipline,
                "score": c.normalized_score,
                "raw_score": c.raw_score,
            }
            for c in cands[:top_k]
        ]
