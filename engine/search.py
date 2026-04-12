"""Índice BM25 por silo (disciplina) sobre Markdown em content/."""

from __future__ import annotations

import logging
import re
import threading
import time
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from core.config import GlobalContextMode
from core.config import Settings
from engine.database import fetch_db_chunks

log = logging.getLogger(f"kernelbots.{__name__}")

_SAFE_DISCIPLINE_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class SearchEngine:
    """Tokeniza, faz chunk de .md por silo, rebuild e busca com threshold normalizado."""

    def __init__(
        self,
        content_dir: Path,
        score_threshold: float,
        global_context_mode: GlobalContextMode = "geral",
        settings: Settings | None = None,   # <-- adicionar
    ) -> None:
        self._content_dir = content_dir.resolve()
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

    @staticmethod
    def _chunk_markdown(path: Path, content_dir: Path, discipline: str) -> list[dict]:
        text = path.read_text(encoding="utf-8", errors="replace")
        sections: list[dict] = []
        current_header = path.stem
        current_lines: list[str] = []
        rel_source = path.resolve().relative_to(content_dir.resolve()).as_posix()

        for line in text.splitlines():
            if re.match(r"^#{1,3}\s", line):
                if current_lines:
                    sections.append({
                        "text": f"{current_header}\n" + "\n".join(current_lines).strip(),
                        "source": rel_source,
                        "discipline": discipline,
                    })
                current_header = line.lstrip("#").strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append({
                "text": f"{current_header}\n" + "\n".join(current_lines).strip(),
                "source": rel_source,
                "discipline": discipline,
            })

        return [s for s in sections if s["text"].strip()]

    def _scan_discipline_ids(self) -> frozenset[str]:
        ids: set[str] = {"geral"}
        if not self._content_dir.is_dir():
            return frozenset(ids)
        for p in self._content_dir.iterdir():
            if p.is_dir() and not p.name.startswith("."):
                ids.add(p.name)
        return frozenset(ids)

    def _collect_files_per_silo(self) -> dict[str, list[Path]]:
        files_by_silo: dict[str, list[Path]] = {"geral": []}
        if not self._content_dir.is_dir():
            return files_by_silo

        root_md = sorted(self._content_dir.glob("*.md"))
        files_by_silo["geral"].extend(root_md)

        geral_sub = self._content_dir / "geral"
        if geral_sub.is_dir():
            files_by_silo["geral"].extend(sorted(geral_sub.rglob("*.md")))

        for child in sorted(self._content_dir.iterdir(), key=lambda x: x.name):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if child.name == "geral":
                continue
            files_by_silo[child.name] = sorted(child.rglob("*.md"))

        return files_by_silo

    def rebuild(self) -> None:
        t0 = time.perf_counter()
        discipline_ids = self._scan_discipline_ids()
        files_by_silo = self._collect_files_per_silo()

        new_silos: dict[str, dict[str, Any]] = {}
        all_chunks: list[dict] = []

        for silo in sorted(discipline_ids):
            paths = files_by_silo.get(silo, [])
            silo_chunks: list[dict] = []
            for md_file in paths:
                try:
                    before = len(silo_chunks)
                    silo_chunks.extend(
                        self._chunk_markdown(md_file, self._content_dir, silo)
                    )
                    added = len(silo_chunks) - before
                    log.info(
                        "   📄 [%s] %s → %s chunk(s)",
                        silo,
                        md_file.relative_to(self._content_dir).as_posix(),
                        added,
                    )
                except Exception:
                    log.exception(
                        "   ❌ [%s] Falha ao processar %s — ignorado",
                        silo,
                        md_file,
                    )

            tokenized = [self._tokenize(c["text"]) for c in silo_chunks]
            bm25 = BM25Okapi(tokenized) if tokenized else None
            new_silos[silo] = {"chunks": silo_chunks, "bm25": bm25}
            all_chunks.extend(silo_chunks)

        if not all_chunks:
            log.warning(
                "⚠  Nenhum .md indexado — BM25 desativado. Modo assistente geral ativo."
            )
                
        # --- chunks do MySQL (silo "db") ---
        db_chunks: list[dict] = []
        if self._settings is not None:
            db_chunks = fetch_db_chunks(self._settings)
        if db_chunks:
            tokenized_db = [self._tokenize(c["text"]) for c in db_chunks]
            new_silos["db"] = {"chunks": db_chunks, "bm25": BM25Okapi(tokenized_db)}
            all_chunks.extend(db_chunks)

        elapsed = (time.perf_counter() - t0) * 1000
        with self._lock:
            self._discipline_ids = discipline_ids
            self._silos = new_silos
            self._all_chunks = all_chunks

        db_count = len(db_chunks)
        md_count = len(all_chunks) - db_count
        log.info(
            "✅ Índice BM25 por silo pronto — %s chunk(s) (%s .md + %s MySQL) | %s silo(s) | rebuild em %.1fms",
            len(all_chunks), md_count, db_count, len(new_silos), elapsed,
        )

    def normalize_discipline(self, raw: str | None) -> str | None:
        """Whitelist contra pastas reais; rejeita path traversal e caracteres inseguros."""
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
                return list(self._silos.get("geral", {}).get("chunks", []))
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
                hits = self._hits_in_silo("geral", query, top_k)
                hits += self._hits_in_silo("db", query, top_k)
                hits.sort(key=lambda h: h["score"], reverse=True)
                return hits[:top_k]

            merged: list[dict] = []
            for silo in sorted(self._silos.keys()):
                merged.extend(self._hits_in_silo(silo, query, top_k))
            merged.sort(key=lambda h: h["score"], reverse=True)
            return merged[:top_k]
