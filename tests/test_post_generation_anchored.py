"""Testes de pós-geração calibrados para grounding anchored."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.retrieval import (
    RetrievalCandidate,
    anchored_post_generation_advisory_flags,
    post_generation_flags,
)


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

    def test_anchored_never_flags_missing_informative_terms(self) -> None:
        answer = "Explicação geral sem repetir os termos da query."
        flags = post_generation_flags(
            answer,
            ("termo", "teste"),
            [_candidate()],
            grounding_policy="anchored",
            decision_reason="ok",
        )
        self.assertNotIn("missing_informative_terms", flags)

    def test_anchored_fonte_citation_skips_missing_source_entities(self) -> None:
        answer = "Segundo [Fonte: aula.json], o conceito aplica-se ao caso."
        flags = post_generation_flags(
            answer,
            ("termo",),
            [_candidate(text="outro material sem overlap")],
            grounding_policy="anchored",
            decision_reason="ok",
        )
        self.assertNotIn("missing_source_entities", flags)

    def test_anchored_advisory_only_strong_flags(self) -> None:
        weak = ["missing_source_entities", "missing_informative_terms"]
        self.assertEqual(anchored_post_generation_advisory_flags(weak), [])
        strong = ["introduced_unsupported_terms"]
        self.assertEqual(
            anchored_post_generation_advisory_flags(strong, "texto sem fonte"),
            strong,
        )

    def test_anchored_advisory_suppressed_with_fonte_citation(self) -> None:
        answer = "Facto [Fonte: db:python/aula.json] e mais texto."
        flags = ["introduced_unsupported_terms"]
        self.assertEqual(anchored_post_generation_advisory_flags(flags, answer), [])

    def test_anchored_advisory_suppressed_on_lacuna_refusal(self) -> None:
        answer = "Lacuna declarada: o material injectado neste turno não cobre Kubernetes."
        flags = ["introduced_unsupported_terms"]
        self.assertEqual(anchored_post_generation_advisory_flags(flags, answer), [])

    def test_anchored_skips_unsupported_when_cites_sources(self) -> None:
        noise = " ".join(f"termoextra{i}" for i in range(40))
        answer = f"[Fonte: db:python/a.json] Explicação {noise}"
        flags = post_generation_flags(
            answer,
            ("termo",),
            [_candidate(text="aula curta")],
            grounding_policy="anchored",
            decision_reason="ok",
        )
        self.assertNotIn("introduced_unsupported_terms", flags)


if __name__ == "__main__":
    unittest.main()
