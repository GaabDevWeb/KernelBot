"""Testes do gate pós-geração advisory vs override."""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.chat_provider import ChatProvider
from engine.context import ContextTrace
from engine.retrieval import RetrievalCandidate, RetrievalDecision, RetrievalTrace


def _collect_override_events(provider: ChatProvider, policy: str) -> list[dict]:
    settings = MagicMock()
    settings.grounding_policy = policy
    provider._settings = settings

    candidate = RetrievalCandidate(
        source="db:python/a.json",
        chunk_id="1",
        text="material da aula",
        discipline="python",
        raw_score=2.0,
        normalized_score=0.5,
        matched_terms=("termo",),
    )
    trace = RetrievalTrace(
        query="termo x",
        normalized_query="termo x",
        informative_terms=("termo", "especifico"),
        mode="strict",
    )
    decision = RetrievalDecision(
        allow_generation=True,
        reason="ok",
        confidence="high",
        selected_candidates=(candidate,),
        trace=trace,
    )
    ctx_trace = ContextTrace(
        label="Test",
        sources=("db:python/a.json",),
        mode="strict",
        decision="answer",
        reason="ok",
        confidence="high",
        retrieval_trace=trace,
    )
    answer = "Resposta genérica sem citar fonte nem termos dos trechos."

    async def _run() -> list[dict]:
        metas: list[dict] = []
        async for chunk in provider._maybe_override_post_generation(
            answer, ctx_trace, decision, tokens_used=10,
        ):
            if chunk.startswith("data: [ACL_META]"):
                import json
                metas.append(json.loads(chunk[len("data: [ACL_META]") :]))
        return metas

    return asyncio.run(_run())


class TestPostGenerationGate(unittest.TestCase):
    def test_anchored_emits_advisory_not_hard_stop(self) -> None:
        provider = ChatProvider(MagicMock())
        metas = _collect_override_events(provider, "anchored")
        self.assertEqual(len(metas), 1)
        self.assertTrue(metas[0].get("post_generation_advisory"))
        self.assertNotEqual(metas[0].get("decision"), "hard_stop")

    def test_strict_emits_override(self) -> None:
        provider = ChatProvider(MagicMock())
        metas = _collect_override_events(provider, "strict")
        self.assertEqual(len(metas), 1)
        self.assertTrue(metas[0].get("post_generation_override"))
        self.assertEqual(metas[0].get("reason"), "post_generation_misalignment")


if __name__ == "__main__":
    unittest.main()
