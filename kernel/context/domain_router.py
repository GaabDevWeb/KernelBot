"""Domain Router — routing determinístico para scoped retrieval (sem LLM)."""

from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from kernel.disciplines.disciplines import load_disciplines, query_markers_by_discipline

_CONFIG_PATH = Path(__file__).resolve().parent / "domain_experts.json"


@dataclass(frozen=True)
class DomainExpert:
    id: str
    name: str
    keywords: tuple[str, ...]
    aliases: tuple[str, ...]
    retrieval_scope: tuple[str, ...]
    instructions: str | None = None


@dataclass(frozen=True)
class DomainCandidate:
    expert_id: str
    score: float
    raw_hits: int


@dataclass(frozen=True)
class DomainRouteResult:
    """Resultado do Domain Router para um turno."""

    selected_expert: str | None
    selected_experts: tuple[str, ...]
    confidence: float
    candidates: tuple[DomainCandidate, ...]
    retrieval_scopes: tuple[str, ...]
    fallback_global: bool
    multi_domain: bool
    reason: str
    instructions: str | None = None
    router_latency_ms: float = 0.0


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _parse_expert(raw: dict[str, Any]) -> DomainExpert:
    return DomainExpert(
        id=str(raw["id"]).strip(),
        name=str(raw.get("name") or raw["id"]).strip(),
        keywords=tuple(str(k).lower() for k in (raw.get("keywords") or [])),
        aliases=tuple(str(a).lower() for a in (raw.get("aliases") or [])),
        retrieval_scope=tuple(str(s) for s in (raw.get("retrieval_scope") or [])),
        instructions=(str(raw["instructions"]).strip() if raw.get("instructions") else None),
    )


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_domain_experts() -> tuple[DomainExpert, ...]:
    cfg = _load_config()
    experts = [_parse_expert(row) for row in cfg.get("experts", [])]
    # Enriquecer keywords com queryMarkers das disciplinas no scope (SSOT disciplines.json).
    markers_by_disc = query_markers_by_discipline()
    enriched: list[DomainExpert] = []
    for ex in experts:
        extra: set[str] = set(ex.keywords) | set(ex.aliases)
        for silo in ex.retrieval_scope:
            for m in markers_by_disc.get(silo, ()):
                extra.add(m.lower())
        enriched.append(
            DomainExpert(
                id=ex.id,
                name=ex.name,
                keywords=tuple(sorted(extra)),
                aliases=ex.aliases,
                retrieval_scope=ex.retrieval_scope,
                instructions=ex.instructions,
            )
        )
    return tuple(enriched)


def _valid_scopes(expert: DomainExpert, indexed: frozenset[str]) -> tuple[str, ...]:
    valid_discipline_ids = {d.id for d in load_disciplines()}
    out: list[str] = []
    for silo in expert.retrieval_scope:
        if silo in indexed or silo in valid_discipline_ids:
            out.append(silo)
    return tuple(dict.fromkeys(out))


class DomainRouter:
    """Classifica domínio por keywords + contexto recente (determinístico)."""

    def __init__(self, *, indexed_disciplines: frozenset[str] | None = None) -> None:
        self._experts = load_domain_experts()
        cfg = _load_config()
        self._threshold_single = float(cfg.get("threshold_single", 0.35))
        self._threshold_multi = float(cfg.get("threshold_multi", 0.2))
        self._multi_gap = float(cfg.get("multi_gap", 0.12))
        self._min_raw_hits = int(cfg.get("min_raw_hits", 1))
        self._indexed = indexed_disciplines or frozenset()

    def _score_expert(self, expert: DomainExpert, text: str) -> tuple[int, float]:
        hits = 0
        weight = 0.0
        for kw in expert.keywords:
            if not kw:
                continue
            if kw in text:
                hits += 1
                weight += max(1.0, len(kw.split()) * 0.5)
        for alias in expert.aliases:
            if alias and alias in text:
                hits += 1
                weight += 1.0
        return hits, weight

    def route(
        self,
        query: str,
        *,
        recent_context: str = "",
    ) -> DomainRouteResult:
        t0 = time.perf_counter()
        # Query pesa mais que contexto recente (sinal, não query RAG).
        q = _normalize_text(query)
        ctx = _normalize_text(recent_context)
        combined = q if not ctx else f"{q} {ctx}"

        raw_scores: list[tuple[DomainExpert, int, float]] = []
        for expert in self._experts:
            q_hits, q_weight = self._score_expert(expert, q)
            ctx_hits, ctx_weight = self._score_expert(expert, ctx) if ctx else (0, 0.0)
            hits = q_hits + (1 if ctx_hits and not q_hits else 0)
            weight = q_weight + ctx_weight * 0.35
            if hits > 0 or weight > 0:
                raw_scores.append((expert, hits, weight))

        if not raw_scores:
            return DomainRouteResult(
                selected_expert=None,
                selected_experts=(),
                confidence=0.0,
                candidates=(),
                retrieval_scopes=(),
                fallback_global=True,
                multi_domain=False,
                reason="no_keyword_hits",
                router_latency_ms=(time.perf_counter() - t0) * 1000,
            )

        max_weight = max(w for _, _, w in raw_scores) or 1.0
        candidates: list[DomainCandidate] = []
        exp_scores: list[tuple[DomainExpert, float, int]] = []
        for expert, hits, weight in raw_scores:
            if hits < self._min_raw_hits and weight <= 0:
                continue
            norm = weight / max_weight
            exp_scores.append((expert, norm, hits))
            candidates.append(DomainCandidate(expert_id=expert.id, score=round(norm, 4), raw_hits=hits))

        if not exp_scores:
            return DomainRouteResult(
                selected_expert=None,
                selected_experts=(),
                confidence=0.0,
                candidates=tuple(candidates),
                retrieval_scopes=(),
                fallback_global=True,
                multi_domain=False,
                reason="below_min_hits",
                router_latency_ms=(time.perf_counter() - t0) * 1000,
            )

        # Softmax leve para confiança interpretável (0–1).
        exp_vals = [s for _, s, _ in exp_scores]
        m = max(exp_vals)
        exps = [math.exp(v - m) for v in exp_vals]
        denom = sum(exps) or 1.0
        probs = [e / denom for e in exps]

        ranked = sorted(
            zip(exp_scores, probs, strict=False),
            key=lambda item: item[1],
            reverse=True,
        )
        (top_expert, top_raw, top_hits), top_prob = ranked[0]
        second_prob = ranked[1][1] if len(ranked) > 1 else 0.0

        candidates_sorted = tuple(
            sorted(candidates, key=lambda c: c.score, reverse=True)
        )

        if top_prob < self._threshold_single and top_raw < self._threshold_multi:
            return DomainRouteResult(
                selected_expert=None,
                selected_experts=(),
                confidence=round(top_prob, 4),
                candidates=candidates_sorted,
                retrieval_scopes=(),
                fallback_global=True,
                multi_domain=False,
                reason="low_confidence",
                router_latency_ms=(time.perf_counter() - t0) * 1000,
            )

        multi = (
            len(ranked) > 1
            and second_prob >= self._threshold_multi
            and (top_prob - second_prob) <= self._multi_gap
        )

        selected_experts: tuple[str, ...]
        scopes: list[str] = []
        instructions: list[str] = []

        if multi:
            selected_experts = (
                ranked[0][0][0].id,
                ranked[1][0][0].id,
            )
            expert_by_id = {e.id: e for e, _, _ in exp_scores}
            for ex_id in selected_experts:
                ex = expert_by_id[ex_id]
                scopes.extend(_valid_scopes(ex, self._indexed))
                if ex.instructions:
                    instructions.append(ex.instructions)
            reason = "multi_domain"
        else:
            selected_experts = (top_expert.id,)
            scopes.extend(_valid_scopes(top_expert, self._indexed))
            if top_expert.instructions:
                instructions.append(top_expert.instructions)
            reason = "single_domain"

        scopes_unique = tuple(dict.fromkeys(scopes))
        if not scopes_unique:
            return DomainRouteResult(
                selected_expert=top_expert.id,
                selected_experts=selected_experts,
                confidence=round(top_prob, 4),
                candidates=candidates_sorted,
                retrieval_scopes=(),
                fallback_global=True,
                multi_domain=multi,
                reason="empty_scope",
                router_latency_ms=(time.perf_counter() - t0) * 1000,
            )

        instr = " ".join(instructions[:2]).strip() or None
        if instr and len(instr) > 240:
            instr = instr[:237] + "…"

        return DomainRouteResult(
            selected_expert=selected_experts[0],
            selected_experts=selected_experts,
            confidence=round(top_prob, 4),
            candidates=candidates_sorted,
            retrieval_scopes=scopes_unique,
            fallback_global=False,
            multi_domain=multi,
            reason=reason,
            instructions=instr,
            router_latency_ms=(time.perf_counter() - t0) * 1000,
        )
