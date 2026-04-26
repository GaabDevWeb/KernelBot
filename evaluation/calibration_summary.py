"""Resumo estatístico dos traces de calibração.

Lê `evaluation/calibration_traces.jsonl` e imprime, sem emojis:

- distribuição por `decision` e `reason`;
- percentis de `top_score` para casos `answer` (base empírica para MIN_SCORE);
- percentis de `coverage` para casos `answer` (base para MIN_COVERAGE);
- `Stop vs Answer Ratio`, `Ambiguous Retrieval Rate`, etc.

Uso:

    python -m evaluation.calibration_summary --traces evaluation/calibration_traces.jsonl
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Iterable


def _load(path: Path) -> list[dict]:
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _percentiles(values: list[float], percentiles: tuple[int, ...] = (10, 20, 50, 80, 90)) -> dict:
    if not values:
        return {f"p{p}": None for p in percentiles}
    sv = sorted(values)
    out: dict[str, float] = {}
    for p in percentiles:
        idx = max(0, min(len(sv) - 1, int(round((p / 100.0) * (len(sv) - 1)))))
        out[f"p{p}"] = sv[idx]
    return out


def summarize(traces: Iterable[dict]) -> dict:
    items = list(traces)
    decision_counter = Counter(t.get("decision", "unknown") for t in items)
    reason_counter = Counter(t.get("reason", "unknown") for t in items)
    flow_counter = Counter(t.get("flow", "unknown") for t in items)

    answer_top_scores = [
        float(t["top_score"])
        for t in items
        if t.get("decision") == "answer" and "top_score" in t
    ]
    answer_coverage = [
        float(t["coverage"])
        for t in items
        if t.get("decision") == "answer" and "coverage" in t
    ]
    hard_stop_top_scores = [
        float(t["top_score"])
        for t in items
        if t.get("decision") == "hard_stop" and "top_score" in t
    ]

    total = len(items)
    answers = decision_counter.get("answer", 0)
    hard_stops = decision_counter.get("hard_stop", 0)

    return {
        "total": total,
        "decisions": dict(decision_counter),
        "reasons": dict(reason_counter),
        "flows": dict(flow_counter),
        "answer_top_score_percentiles": _percentiles(answer_top_scores),
        "answer_top_score_min": min(answer_top_scores) if answer_top_scores else None,
        "answer_top_score_mean": statistics.mean(answer_top_scores) if answer_top_scores else None,
        "answer_coverage_percentiles": _percentiles(answer_coverage),
        "hard_stop_top_score_percentiles": _percentiles(hard_stop_top_scores),
        "stop_vs_answer_ratio": (
            f"{hard_stops}:{answers}" if total else "0:0"
        ),
        "ambiguous_retrieval_rate": (
            reason_counter.get("ambiguous_retrieval", 0) / total if total else 0.0
        ),
        "underspecified_query_rate": (
            reason_counter.get("underspecified_query", 0) / total if total else 0.0
        ),
        "vague_but_high_risk_rate": (
            reason_counter.get("vague_but_high_risk", 0) / total if total else 0.0
        ),
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--traces", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)

    items = _load(args.traces)
    summary = summarize(items)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
