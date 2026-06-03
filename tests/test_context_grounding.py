"""Testes mínimos de contratos de grounding condicionais."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Raiz do projeto no PYTHONPATH
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.context import _format_chunks_for_prompt, _select_grounding
from engine.retrieval import RetrievalCandidate, RetrievalDecision, RetrievalTrace, build_decision


def _mock_settings(
    *,
    retrieval_mode: str = "strict",
    disambiguation_enabled: bool = False,
    grounding_policy: str = "anchored",
) -> MagicMock:
    s = MagicMock()
    s.retrieval_mode = retrieval_mode
    s.disambiguation_enabled = disambiguation_enabled
    s.grounding_policy = grounding_policy
    s.grounding_strict = "GROUNDING_STRICT"
    s.grounding_anchored = "GROUNDING_ANCHORED"
    s.grounding_permissive = "GROUNDING_PERMISSIVE"
    s.grounding_disambiguation = "GROUNDING_DISAMBIGUATION"
    return s


def _fake_decision(
    reason: str,
    *,
    allow: bool = True,
    candidates: tuple[RetrievalCandidate, ...] = (),
) -> RetrievalDecision:
    trace = RetrievalTrace(
        query="q",
        normalized_query="q",
        informative_terms=("termo", "teste"),
        mode="strict",
    )
    return RetrievalDecision(
        allow_generation=allow,
        reason=reason,  # type: ignore[arg-type]
        confidence="low",
        selected_candidates=candidates,
        trace=trace,
    )


def _candidate(source: str = "a.json") -> RetrievalCandidate:
    return RetrievalCandidate(
        source=source,
        chunk_id=f"id-{source}",
        text=f"conteudo {source}",
        discipline="python",
        raw_score=2.0,
        normalized_score=0.2,
        matched_terms=("termo",),
    )


class TestSelectGrounding(unittest.TestCase):
    def test_anchored_ok_uses_anchored(self) -> None:
        d = _fake_decision("ok", candidates=(_candidate(),))
        s = _mock_settings(grounding_policy="anchored")
        self.assertEqual(_select_grounding(d, s), s.grounding_anchored)

    def test_strict_ok_uses_strict(self) -> None:
        d = _fake_decision("ok", candidates=(_candidate(),))
        s = _mock_settings(grounding_policy="strict")
        self.assertEqual(_select_grounding(d, s), s.grounding_strict)

    def test_hybrid_insufficient_without_chunks_uses_permissive(self) -> None:
        d = _fake_decision("insufficient_context")
        s = _mock_settings(grounding_policy="hybrid")
        self.assertEqual(_select_grounding(d, s), s.grounding_permissive)

    def test_hybrid_insufficient_with_chunks_uses_anchored(self) -> None:
        d = _fake_decision("insufficient_context", candidates=(_candidate(),))
        s = _mock_settings(grounding_policy="hybrid")
        self.assertEqual(_select_grounding(d, s), s.grounding_anchored)

    def test_ambiguous_with_flag_uses_disambiguation(self) -> None:
        d = _fake_decision("ambiguous_retrieval")
        s = _mock_settings(disambiguation_enabled=True)
        self.assertEqual(_select_grounding(d, s), s.grounding_disambiguation)

    def test_strict_insufficient_uses_strict(self) -> None:
        d = _fake_decision("insufficient_context")
        s = _mock_settings(grounding_policy="strict")
        self.assertEqual(_select_grounding(d, s), s.grounding_strict)


class TestGroundingAnchoredFile(unittest.TestCase):
    def test_grounding_anchored_file_exists(self) -> None:
        path = _ROOT / "core" / "systemPrompt" / "grounding_anchored.txt"
        self.assertTrue(path.is_file(), f"ficheiro em falta: {path}")
        self.assertIn("evidência primária", path.read_text(encoding="utf-8").lower())


class TestFormatChunks(unittest.TestCase):
    def test_numbered_sources_when_disambiguation(self) -> None:
        d = _fake_decision("ambiguous_retrieval")
        s = _mock_settings(disambiguation_enabled=True)
        selected = [
            {"source": "a.json", "text": "texto A", "normalized_score": 0.9},
            {"source": "b.json", "text": "texto B", "normalized_score": 0.85},
        ]
        out = _format_chunks_for_prompt(selected, d, s)
        self.assertIn("[Fonte 1: a.json | Score: 0.90]", out)
        self.assertIn("[Fonte 2: b.json | Score: 0.85]", out)

    def test_standard_fonte_label(self) -> None:
        d = _fake_decision("ok")
        s = _mock_settings()
        selected = [{"source": "x.json", "text": "corpo", "normalized_score": 1.0}]
        out = _format_chunks_for_prompt(selected, d, s)
        self.assertIn("[Fonte: x.json | Score: 1.00]", out)


class TestBuildDecisionPolicy(unittest.TestCase):
    def _candidate_score(self, source: str, score: float) -> RetrievalCandidate:
        return RetrievalCandidate(
            source=source,
            chunk_id=f"id-{source}",
            text=f"conteudo {source}",
            discipline="python",
            raw_score=score,
            normalized_score=score / 10.0,
            matched_terms=("termo",),
        )

    def test_fallback_allows_generation_without_hits(self) -> None:
        d = build_decision("termo teste", [], acl_retrieval_mode="fallback")
        self.assertTrue(d.allow_generation)
        self.assertEqual(d.reason, "insufficient_context")

    def test_always_allows_generation_without_hits(self) -> None:
        d = build_decision("termo teste", [], acl_retrieval_mode="strict")
        self.assertTrue(d.allow_generation)
        self.assertEqual(d.reason, "insufficient_context")
        self.assertEqual(d.selected_candidates, ())

    def test_underspecified_query_includes_weak_chunks(self) -> None:
        c = self._candidate_score("a.json", 2.0)
        d = build_decision("x", [c], min_terms=2)
        self.assertTrue(d.allow_generation)
        self.assertEqual(d.reason, "underspecified_query")
        self.assertGreaterEqual(len(d.selected_candidates), 1)

    def test_context_misaligned_includes_chunks(self) -> None:
        c = RetrievalCandidate(
            source="a.json",
            chunk_id="id-a",
            text="texto sem termos da query",
            discipline="python",
            raw_score=3.0,
            normalized_score=0.3,
            matched_terms=(),
        )
        d = build_decision(
            "termo especifico longo",
            [c],
            min_coverage=0.99,
        )
        self.assertTrue(d.allow_generation)
        self.assertEqual(d.reason, "context_misaligned")
        self.assertGreaterEqual(len(d.selected_candidates), 1)

    def test_ambiguous_without_flag_allows_with_chunks(self) -> None:
        c1 = self._candidate_score("a.json", 2.0)
        c2 = self._candidate_score("b.json", 1.9)
        d = build_decision(
            "termo teste especifico",
            [c1, c2],
            disambiguation_enabled=False,
            min_score_margin=0.15,
        )
        self.assertTrue(d.allow_generation)
        self.assertEqual(d.reason, "ambiguous_retrieval")
        self.assertGreaterEqual(len(d.selected_candidates), 2)

    def test_disambiguation_allows_two_qualified(self) -> None:
        c1 = self._candidate_score("a.json", 2.0)
        c2 = self._candidate_score("b.json", 1.9)
        d = build_decision(
            "termo teste especifico",
            [c1, c2],
            disambiguation_enabled=True,
            min_score_margin=0.15,
        )
        self.assertTrue(d.allow_generation)
        self.assertEqual(d.reason, "ambiguous_retrieval")
        self.assertGreaterEqual(len(d.selected_candidates), 2)


if __name__ == "__main__":
    unittest.main()
