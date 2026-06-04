"""Testes de merge pin + sticky no prompt."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.context import ContextManager, _merge_pin_and_retrieval_chunks
from engine.pinned_store import PinnedContext, PinnedSessionStore
from engine.retrieval import RetrievalCandidate


class TestMergePinChunks(unittest.TestCase):
    def test_pin_prepended_and_deduped(self) -> None:
        pin = PinnedContext(
            scope_key="discipline:python",
            chunks=[{"source": "db:python/a", "text": "texto pin"}],
            display_name="Aula A",
        )
        retrieval = [
            {"source": "db:python/a", "text": "texto novo"},
            {"source": "db:python/b", "text": "texto b"},
        ]
        merged = _merge_pin_and_retrieval_chunks(pin, retrieval, max_chars=50_000)
        sources = [m["source"] for m in merged]
        self.assertEqual(sources[0], "db:python/a")
        self.assertEqual(merged[0]["text"], "texto pin")
        self.assertIn("db:python/b", sources)
        self.assertEqual(len(sources), 2)


class TestPinInBuildMessages(unittest.TestCase):
    def _manager_with_pin(self) -> tuple[ContextManager, str]:
        settings = MagicMock()
        settings.system_prompt_geral = "BASE PROMPT"
        settings.catalog_router_prompt = "CATALOG ROUTER"
        settings.sticky_instruction = "STICKY TEMA: {name}"
        settings.grounding_strict = "GROUNDING_STRICT"
        settings.grounding_anchored = "GROUNDING_ANCHORED"
        settings.grounding_permissive = "GROUNDING_PERMISSIVE"
        settings.grounding_disambiguation = "GROUNDING_DISAMBIGUATION"
        settings.grounding_policy = "anchored"
        settings.disambiguation_enabled = False
        settings.retrieval_mode = "strict"
        settings.global_context_mode = "geral"
        settings.pinned_max_chars = 24_000
        settings.pinned_max_turns = 5
        settings.retrieval_min_score = 0.0
        settings.retrieval_min_score_margin = 0.0
        settings.retrieval_min_coverage = 0.0
        settings.retrieval_min_coverage_weighted = 0.0
        settings.retrieval_min_terms = 1
        settings.retrieval_candidate_k = 8
        settings.retrieval_top_k = 4
        settings.retrieval_max_chunks_per_source = 2
        settings.catalog_enabled = False

        candidate = RetrievalCandidate(
            source="db:python/aula-teste",
            chunk_id="c1",
            text="conteudo sobre list comprehension em python",
            discipline="python",
            raw_score=5.0,
            normalized_score=0.9,
            matched_terms=("list", "comprehension"),
        )

        search = MagicMock()
        search.normalize_discipline = lambda d: d
        search.search_candidates = MagicMock(return_value=[candidate])

        store = PinnedSessionStore()
        session_id = "test-session-pin-001"
        store.set_pinned(
            session_id,
            "discipline:python",
            [{"source": "db:python/pin-old", "text": "contexto fixado da aula anterior"}],
            "Aula Pinada",
            max_turns=5,
        )

        mgr = ContextManager(
            settings,
            search,
            pinned_store=store,
            lesson_catalog=None,
            indexed_lesson_keys=set(),
        )
        return mgr, session_id

    def test_system_contains_sticky_and_pin_text(self) -> None:
        mgr, session_id = self._manager_with_pin()
        result = mgr.build_messages(
            "exemplo com list comprehension",
            session_id=session_id,
        )
        system = result.messages[0]["content"]
        self.assertIn("STICKY TEMA: Aula Pinada", system)
        self.assertIn("contexto fixado da aula anterior", system)
        self.assertTrue(result.trace.pin_chunks_used)


if __name__ == "__main__":
    unittest.main()
