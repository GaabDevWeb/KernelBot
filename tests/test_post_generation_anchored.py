"""Testes de pós-geração calibrados para grounding anchored."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.retrieval import RetrievalCandidate, post_generation_flags


def _candidate(source: str = "aula.json", text: str = "conteudo da aula sobre termo teste") -> RetrievalCandidate:
    return RetrievalCandidate(
        source=source,
        chunk_id="id-1",
        text=text,
        discipline="python",
        raw_score=2.0,
        normalized_score=0.5,
        matched_terms=("termo", "teste"),
    )


class TestPostGenerationAnchored(unittest.TestCase):
    def test_anchored_pedagogical_extension_skips_missing_source_entities(self) -> None:
        answer = (
            "Segundo [Fonte: aula.json], o critério X aplica-se.\n\n"
            "*Extensão pedagógica (fora do material indexado):*\n"
            "Analogia genérica para fixar o conceito."
        )
        flags = post_generation_flags(
            answer,
            ("termo", "teste"),
            [_candidate()],
            grounding_policy="anchored",
            decision_reason="ok",
        )
        self.assertNotIn("missing_source_entities", flags)

    def test_strict_still_flags_missing_source_entities(self) -> None:
        answer = "Resposta genérica longa sem citar fonte nem termos dos trechos indexados."
        flags = post_generation_flags(
            answer,
            ("termo", "teste"),
            [_candidate(text="termo teste especifico do material da aula")],
            grounding_policy="strict",
            decision_reason="ok",
        )
        self.assertIn("missing_source_entities", flags)

    def test_pedagogical_marker_only_no_missing_source(self) -> None:
        answer = (
            "[Fonte: aula.json] Facto do curso.\n\n"
            "*Extensão pedagógica (fora do material indexado):*\n"
            "Analogia livre."
        )
        flags = post_generation_flags(
            answer,
            ("termo",),
            [_candidate()],
            grounding_policy="anchored",
            decision_reason="ok",
        )
        self.assertNotIn("missing_source_entities", flags)

    def test_anchored_skips_informative_terms_when_reason_not_ok(self) -> None:
        answer = "Explicação geral sem repetir os termos da query."
        flags = post_generation_flags(
            answer,
            ("termo", "teste"),
            [_candidate()],
            grounding_policy="anchored",
            decision_reason="insufficient_context",
        )
        self.assertNotIn("missing_informative_terms", flags)


if __name__ == "__main__":
    unittest.main()
