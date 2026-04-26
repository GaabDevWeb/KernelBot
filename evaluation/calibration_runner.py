"""Gera traços de retrieval para calibração manual (Fases 1, 2 e 3).

Objetivo: produzir o artefato exigido pelo plano incremental RAG ACL —
uma amostra de 20 casos com `query`, `top_score`, `second_score`,
`score_margin`, coverage, fontes selecionadas, decisão, motivo e
confiança, para que um humano marque cada caso como hit correto, falso
bloqueio, resposta sem base, etc.

Este script NÃO chama o LLM. Ele só roda o retrieval lexical e a decisão
e grava o trace em JSONL.

Uso:

    python -m evaluation.calibration_runner \
        --questions evaluation/all.md \
        --out evaluation/calibration_traces.jsonl \
        --limit 20

Saída: JSONL com uma linha por query. Cada linha contém o trace
serializado mais um campo vazio `manual_label` que o humano preenche
durante a revisão (ex.: "correct_answer_with_base",
"false_confidence_risk", "false_block").
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from core.structured_log import ACL_MOD_EVALUATION, log_event
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import Settings
from core.logging_config import configure_logging
from engine.retrieval import build_decision, select_mode
from engine.search import SearchEngine

_log_eval = logging.getLogger("kernelbots.evaluation.calibration")


_QUESTION_LINE_RE = re.compile(r"^(/[A-Za-z][A-Za-z0-9-]*)\s+(.+?)\s*$")


def parse_questions(path: Path) -> list[tuple[str | None, str, str]]:
    """Parse o questions.md/all.md: [(discipline, query, raw_line)].

    Aceita linhas como:

        /python como usar variavel
        /content performance
        /visualizacao-sql sql select group by

    Ignora linhas com apenas emoji/título.
    """
    out: list[tuple[str | None, str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _QUESTION_LINE_RE.match(line)
        if not m:
            continue
        cmd, rest = m.group(1), m.group(2).strip()
        discipline: str | None = None
        if cmd == "/doc":
            discipline = "doc"
            query = rest
        elif cmd == "/content":
            discipline = None
            query = rest
        else:
            discipline = cmd.lstrip("/")
            query = rest
        out.append((discipline, query, line))
    return out


def _mode_for(discipline: str | None) -> str:
    return select_mode(
        force_doc=discipline == "doc",
        force_rag=discipline is not None and discipline != "doc",
        discipline_from_command=discipline if discipline and discipline != "doc" else None,
        has_explicit_assistive_flag=False,
    )


def run(
    questions_path: Path,
    out_path: Path,
    limit: int | None = None,
) -> int:
    configure_logging()
    settings = Settings.load()
    engine = SearchEngine(
        settings.bm25_score_threshold,
        settings.global_context_mode,
        settings=settings,
    )

    items = parse_questions(questions_path)
    if limit is not None:
        items = items[:limit]

    with out_path.open("w", encoding="utf-8") as f:
        for discipline, query, raw_line in items:
            mode = _mode_for(discipline)

            if discipline == "doc":
                # /doc é fluxo determinístico no ContextManager: injeta todos
                # os chunks do silo `doc` sem passar por decisão. Para
                # calibração, registramos esse caso explicitamente.
                doc_chunks = [c for c in engine.chunks if c.get("discipline") == "doc"]
                record = {
                    "raw_line": raw_line,
                    "discipline": discipline,
                    "query": query,
                    "mode": mode,
                    "flow": "doc_injection",
                    "num_doc_chunks": len(doc_chunks),
                    "decision": "answer" if doc_chunks else "hard_stop",
                    "reason": "ok" if doc_chunks else "insufficient_context",
                    "llm_called": bool(doc_chunks),
                    "manual_label": "",
                    "manual_notes": "",
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                continue

            candidates = engine.search_candidates(
                query,
                candidate_k=settings.retrieval_candidate_k,
                discipline_filter=discipline,
            )

            decision = build_decision(
                query=query,
                candidates=candidates,
                mode=mode,
                min_score=settings.retrieval_min_score,
                min_score_margin=settings.retrieval_min_score_margin,
                min_coverage=settings.retrieval_min_coverage,
                min_coverage_weighted=settings.retrieval_min_coverage_weighted,
                min_terms=settings.retrieval_min_terms,
                top_k=settings.retrieval_top_k,
                max_per_source=settings.retrieval_max_chunks_per_source,
            )
            record = {
                "raw_line": raw_line,
                "discipline": discipline,
                "query": query,
                "mode": mode,
                "flow": "retrieval_decision",
                **decision.trace.to_dict(),
                # placeholders para revisão humana.
                "manual_label": "",
                "manual_notes": "",
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return len(items)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera traces de calibração de retrieval.")
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    n = run(args.questions, args.out, limit=args.limit)
    log_event(
        _log_eval,
        logging.INFO,
        ACL_MOD_EVALUATION,
        "calibration_run_complete",
        "JSONL de calibracao escrito",
        metadata={"lines_written": n, "out": str(args.out), "questions": str(args.questions)},
    )
    # ASCII-safe para Windows cp1252.
    print(f"[OK] Gerados {n} traces em {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
