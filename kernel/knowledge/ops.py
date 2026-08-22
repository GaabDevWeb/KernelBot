"""Helpers Ops Center P1 — Conhecimento (listagem, busca, RAG debug, reindex)."""

from __future__ import annotations

import re
import time
from collections import Counter
from typing import Any, Literal

from kernel.knowledge.catalog_sync import refresh_indexed_lesson_keys_state
from kernel.knowledge.database import fetch_db_document_meta
from kernel.rag.retrieval import build_decision, expand_query_tokens, select_mode
from kernel.schemas.chat import confidence_to_float

SearchMode = Literal["bm25", "hybrid", "full"]
ReindexScope = Literal["all", "discipline", "document"]

_SOURCE_RE = re.compile(r"^db:([^/]+)/(.+)$")
_SNIPPET_DEFAULT = 280


def _parse_source(source: str) -> tuple[str, str]:
    m = _SOURCE_RE.match(source or "")
    if m:
        return m.group(1), m.group(2)
    return "", source or ""


def _chunk_counts(engine: Any) -> Counter[str]:
    counts: Counter[str] = Counter()
    for chunk in engine.chunks:
        src = str(chunk.get("source") or "")
        if src:
            counts[src] += 1
    return counts


def list_documents(
    services: Any,
    *,
    q: str = "",
    discipline: str = "",
    limit: int = 500,
) -> dict[str, Any]:
    """Lista documentos com disciplina, slug/título, chunks e data de ingestão."""
    settings = services.context_manager.settings
    engine = services.search_engine
    counts = _chunk_counts(engine)
    meta_rows = fetch_db_document_meta(settings)
    by_source: dict[str, dict[str, Any]] = {}

    for row in meta_rows:
        src = str(row["source"])
        by_source[src] = {
            "discipline": row["discipline"],
            "slug": row["slug"],
            "title": row["title"],
            "source": src,
            "chunks": counts.get(src, 0),
            "updated_at": row.get("updated_at"),
            "from_db": True,
        }

    for src, n in counts.items():
        if src in by_source:
            by_source[src]["chunks"] = n
            continue
        disc, slug = _parse_source(src)
        by_source[src] = {
            "discipline": disc or "?",
            "slug": slug or src,
            "title": slug or src,
            "source": src,
            "chunks": n,
            "updated_at": None,
            "from_db": False,
        }

    items = list(by_source.values())
    q_norm = (q or "").strip().lower()
    disc_norm = (discipline or "").strip().lower()
    if disc_norm:
        items = [i for i in items if str(i["discipline"]).lower() == disc_norm]
    if q_norm:
        items = [
            i
            for i in items
            if q_norm in str(i["title"]).lower()
            or q_norm in str(i["slug"]).lower()
            or q_norm in str(i["discipline"]).lower()
            or q_norm in str(i["source"]).lower()
        ]
    items.sort(key=lambda i: (str(i["discipline"]), str(i["slug"])))
    total = len(items)
    items = items[: max(1, min(limit, 2000))]
    silos = sorted({str(i["discipline"]) for i in by_source.values() if i["discipline"]})
    return {
        "documents": items,
        "total": total,
        "shown": len(items),
        "index_chunks": len(engine.chunks),
        "silos": silos,
        "db_meta_count": len(meta_rows),
    }


def _candidate_row(c: Any, *, snippet_chars: int) -> dict[str, Any]:
    text = str(getattr(c, "text", "") or "")
    return {
        "source": getattr(c, "source", ""),
        "discipline": getattr(c, "discipline", ""),
        "chunk_id": getattr(c, "chunk_id", ""),
        "score": round(float(getattr(c, "raw_score", 0.0) or 0.0), 4),
        "score_normalized": round(float(getattr(c, "normalized_score", 0.0) or 0.0), 4),
        "matched_terms": list(getattr(c, "matched_terms", ()) or ()),
        "snippet": text[:snippet_chars],
        "chunk": text,
        "chunk_chars": len(text),
    }


def run_search(
    services: Any,
    *,
    query: str,
    mode: SearchMode = "hybrid",
    discipline: str | None = None,
    top_k: int = 8,
    snippet_chars: int = _SNIPPET_DEFAULT,
) -> dict[str, Any]:
    """Busca Ops: bm25 (bruto), hybrid (decisão ACL), full (pipeline build_messages)."""
    settings = services.context_manager.settings
    engine = services.search_engine
    q = (query or "").strip()
    top_k = max(1, min(int(top_k or 8), 20))
    disc = (discipline or "").strip() or None
    mode_norm: SearchMode = mode if mode in ("bm25", "hybrid", "full") else "hybrid"

    base_tokens = re.findall(r"\w+", q.lower())
    processed = " ".join(expand_query_tokens(base_tokens)) if base_tokens else q

    if mode_norm == "full":
        built = services.context_manager.build_messages(
            q,
            discipline_filter=disc,
            session_id=None,
            conversation_history=None,
        )
        decision = built.decision
        trace = decision.trace if decision else None
        processed = (trace.normalized_query if trace else processed) or processed
        selected = list(decision.selected_candidates) if decision else []
        considered = list(built.candidates_considered or ())
        rows = [_candidate_row(c, snippet_chars=snippet_chars) for c in selected[:top_k]]
        return {
            "mode": mode_norm,
            "query": q,
            "processed_query": processed,
            "discipline": built.effective_discipline or disc,
            "candidates": rows,
            "candidates_considered": len(considered),
            "reason": decision.reason if decision else None,
            "confidence": decision.confidence if decision else None,
            "confidence_float": confidence_to_float(decision.confidence) if decision else None,
            "decision": "answer" if decision and decision.allow_generation else "hard_stop",
            "top_score": trace.top_score if trace else 0.0,
            "coverage": trace.coverage if trace else 0.0,
            "label": built.trace.label if built.trace else None,
        }

    candidates = engine.search_candidates(
        q,
        candidate_k=min(settings.retrieval_candidate_k, max(top_k, 8)),
        discipline_filter=disc,
    )

    if mode_norm == "bm25":
        rows = [_candidate_row(c, snippet_chars=snippet_chars) for c in candidates[:top_k]]
        return {
            "mode": mode_norm,
            "query": q,
            "processed_query": processed,
            "discipline": disc,
            "candidates": rows,
            "candidates_considered": len(candidates),
            "reason": None,
            "confidence": None,
            "confidence_float": None,
            "decision": None,
            "top_score": candidates[0].raw_score if candidates else 0.0,
            "coverage": None,
            "label": None,
        }

    decision = build_decision(
        query=q,
        candidates=candidates,
        mode=select_mode(False, False, None, False),
        min_score=settings.retrieval_min_score,
        min_score_margin=settings.retrieval_min_score_margin,
        min_coverage=settings.retrieval_min_coverage,
        min_coverage_weighted=settings.retrieval_min_coverage_weighted,
        min_terms=settings.retrieval_min_terms,
        top_k=top_k,
        max_per_source=settings.retrieval_max_chunks_per_source,
        acl_retrieval_mode=settings.retrieval_mode,
        disambiguation_enabled=settings.disambiguation_enabled,
    )
    selected = decision.selected_candidates[:top_k]
    rows = [_candidate_row(c, snippet_chars=snippet_chars) for c in selected]
    return {
        "mode": mode_norm,
        "query": q,
        "processed_query": decision.trace.normalized_query or processed,
        "discipline": disc,
        "candidates": rows,
        "candidates_considered": len(candidates),
        "reason": decision.reason,
        "confidence": decision.confidence,
        "confidence_float": confidence_to_float(decision.confidence),
        "decision": "answer" if decision.allow_generation else "hard_stop",
        "top_score": decision.trace.top_score,
        "coverage": decision.trace.coverage,
        "label": None,
    }


def explore_rag(
    services: Any,
    *,
    question: str,
    discipline: str | None = None,
    snippet_chars: int = 400,
) -> dict[str, Any]:
    """RAG Explorer: mesma rota de retrieval do chat (sem LLM / sem pin)."""
    q = (question or "").strip()
    disc = (discipline or "").strip() or None
    built = services.context_manager.build_messages(
        q,
        discipline_filter=disc,
        session_id=None,
        conversation_history=None,
    )
    decision = built.decision
    trace = decision.trace if decision else None
    considered = [
        _candidate_row(c, snippet_chars=snippet_chars)
        for c in (built.candidates_considered or ())[:20]
    ]
    selected = [
        _candidate_row(c, snippet_chars=snippet_chars)
        for c in (decision.selected_candidates if decision else ())
    ]
    return {
        "question": q,
        "processed_query": (trace.normalized_query if trace else q) or q,
        "informative_terms": list(trace.informative_terms) if trace else [],
        "discipline": built.effective_discipline or disc,
        "label": built.trace.label if built.trace else None,
        "reason": (built.trace.reason if built.trace else None)
        or (decision.reason if decision else None),
        "confidence": decision.confidence if decision else None,
        "confidence_float": confidence_to_float(decision.confidence) if decision else None,
        "top_score": trace.top_score if trace else 0.0,
        "second_score": trace.second_score if trace else 0.0,
        "score_margin": trace.score_margin if trace else 0.0,
        "coverage": trace.coverage if trace else 0.0,
        "retrieval_mode": trace.retrieval_mode if trace else None,
        "top_docs": selected,
        "candidates_considered": considered,
        "sources": list(built.trace.sources) if built.trace else [],
    }


def reindex_knowledge(
    services: Any,
    *,
    scope: ReindexScope = "all",
    discipline: str | None = None,
    document: str | None = None,
    ingest_disk: bool = False,
) -> dict[str, Any]:
    """Reconstrói BM25 (como /reload). Scope disciplina/documento é best-effort (stats)."""
    steps: list[dict[str, Any]] = []
    engine = services.search_engine
    settings = services.context_manager.settings
    disc = (discipline or "").strip() or None
    doc = (document or "").strip() or None
    scope_norm: ReindexScope = scope if scope in ("all", "discipline", "document") else "all"

    if ingest_disk:
        t0 = time.perf_counter()
        try:
            if scope_norm == "discipline" and disc == "doc":
                from kernel.knowledge.wiki_doc import ingest_wiki_to_mysql

                n = ingest_wiki_to_mysql(settings)
                steps.append(
                    {
                        "name": "ingest_wiki",
                        "ok": True,
                        "detail": f"{n} página(s) wiki → MySQL",
                        "ms": round((time.perf_counter() - t0) * 1000, 1),
                    }
                )
            else:
                from kernel.knowledge.jsons_ingest import ingest_jsons_to_mysql

                counts = ingest_jsons_to_mysql(settings)
                total = sum(counts.values())
                detail = f"{total} aula(s)"
                if disc and scope_norm == "discipline":
                    detail += f" (pedido: {disc}; ingest faz UPSERT de todas as disciplinas no disco)"
                steps.append(
                    {
                        "name": "ingest_jsons",
                        "ok": True,
                        "detail": detail,
                        "by_discipline": counts,
                        "ms": round((time.perf_counter() - t0) * 1000, 1),
                    }
                )
        except Exception as exc:
            steps.append(
                {
                    "name": "ingest_disk",
                    "ok": False,
                    "detail": f"{type(exc).__name__}: {exc}",
                    "ms": round((time.perf_counter() - t0) * 1000, 1),
                }
            )

    t1 = time.perf_counter()
    engine.rebuild()
    chunk_total = len(engine.chunks)
    silo_count = len(engine.discipline_ids)
    rebuild_ms = round((time.perf_counter() - t1) * 1000, 1)
    steps.append(
        {
            "name": "rebuild_bm25",
            "ok": True,
            "detail": f"{chunk_total} chunk(s), {silo_count} silo(s)",
            "ms": rebuild_ms,
        }
    )

    t2 = time.perf_counter()
    keys, keys_refreshed = refresh_indexed_lesson_keys_state(services)
    steps.append(
        {
            "name": "refresh_indexed_keys",
            "ok": keys_refreshed,
            "detail": f"{len(keys)} chave(s)"
            + ("" if keys_refreshed else " (falha MySQL — snapshot anterior)"),
            "ms": round((time.perf_counter() - t2) * 1000, 1),
        }
    )

    scope_stats: dict[str, Any] = {"scope": scope_norm}
    if scope_norm == "discipline" and disc:
        silo_chunks = [c for c in engine.chunks if c.get("discipline") == disc]
        scope_stats["discipline"] = disc
        scope_stats["chunks"] = len(silo_chunks)
        scope_stats["note"] = (
            "Rebuild é sempre do índice completo; estatísticas abaixo filtradas pela disciplina."
        )
    elif scope_norm == "document" and doc:
        # aceita source completo ou discipline/slug
        if doc.startswith("db:"):
            src = doc
        elif "/" in doc:
            src = f"db:{doc}" if not doc.startswith("db:") else doc
        else:
            src = doc
        matched = [c for c in engine.chunks if str(c.get("source") or "") == src]
        if not matched and disc:
            alt = f"db:{disc}/{doc}"
            matched = [c for c in engine.chunks if str(c.get("source") or "") == alt]
            src = alt if matched else src
        scope_stats["document"] = src
        scope_stats["chunks"] = len(matched)
        scope_stats["note"] = (
            "Não há rebuild parcial por documento; o índice inteiro foi reconstruído."
        )

    return {
        "steps": steps,
        "chunk_total": chunk_total,
        "silo_count": silo_count,
        "silos": sorted(engine.discipline_ids),
        "scope_stats": scope_stats,
        "ok": all(s.get("ok") for s in steps if s.get("name") != "ingest_disk"),
    }
