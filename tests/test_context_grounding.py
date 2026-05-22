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
) -> MagicMock:
    s = MagicMock()
    s.retrieval_mode = retrieval_mode
    s.disambiguation_enabled = disambiguation_enabled
    s.grounding_strict = "GROUNDING_STRICT"
    s.grounding_permissive = "GROUNDING_PERMISSIVE"
    s.grounding_disambiguation = "GROUNDING_DISAMBIGUATION"
    return s


def _fake_decision(reason: str, *, allow: bool = True, candidates: tuple = ()) -> RetrievalDecision:
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


class TestSelectGrounding(unittest.TestCase):
    def test_strict_insufficient_uses_strict(self) -> None:
        d = _fake_decision("insufficient_context")
        s = _mock_settings(retrieval_mode="strict")
        self.assertEqual(_select_grounding(d, s), s.grounding_strict)

    def test_fallback_insufficient_uses_permissive(self) -> None:
        d = _fake_decision("insufficient_context")
        s = _mock_settings(retrieval_mode="fallback")
        self.assertEqual(_select_grounding(d, s), s.grounding_permissive)

    def test_ambiguous_with_flag_uses_disambiguation(self) -> None:
        d = _fake_decision("ambiguous_retrieval")
        s = _mock_settings(disambiguation_enabled=True)
        self.assertEqual(_select_grounding(d, s), s.grounding_disambiguation)

    def test_ok_uses_strict(self) -> None:
        d = _fake_decision("ok")
        s = _mock_settings()
        self.assertEqual(_select_grounding(d, s), s.grounding_strict)


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
    def _candidate(self, source: str, score: float) -> RetrievalCandidate:
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

    def test_strict_blocks_without_hits(self) -> None:
        d = build_decision("termo teste", [], acl_retrieval_mode="strict")
        self.assertFalse(d.allow_generation)

    def test_disambiguation_allows_two_qualified(self) -> None:
        c1 = self._candidate("a.json", 2.0)
        c2 = self._candidate("b.json", 1.9)
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
