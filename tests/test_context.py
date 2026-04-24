"""Testes de integração do ContextManager.

Cobrem critérios de aceite do plano:

- Pergunta sem contexto não chama LLM (messages inclui assistant pré-montado).
- /content NÃO injeta scope_chunks[:5] (remoção do fallback inseguro).
- ACL_META distingue hard stop de geração permitida.
- Hard stop por retrieval é diferente de provider_error.
"""

from __future__ import annotations

from pathlib import Path
import sys
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import Settings
from engine.context import ContextManager, hard_stop_message
from engine.retrieval import CANDIDATE_K, RetrievalCandidate


def _make_settings(**overrides: Any) -> Settings:
    defaults = dict(
        openrouter_api_key="fake-test-key",
        project_root=Path("."),
        content_dir=Path("."),
        bm25_score_threshold=0.7,
        global_context_mode="geral",
        openrouter_base="https://example.test/chat",
        models=("modelA",),
        system_prompt_geral="SYSTEM_PROMPT_BASE",
        sticky_instruction="Contexto: {name}",
        http_timeout=5.0,
        pinned_max_turns=3,
        pinned_max_chars=4000,
        pinned_weak_score=0.4,
        db_host="",
        db_port=3306,
        db_name="",
        db_user="",
        db_password="",
        retrieval_min_score=1.5,
        retrieval_min_score_margin=0.15,
        retrieval_min_coverage=0.34,
        retrieval_min_coverage_weighted=0.34,
        retrieval_min_terms=2,
        retrieval_candidate_k=CANDIDATE_K,
        retrieval_top_k=4,
        retrieval_max_chunks_per_source=2,
    )
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


@dataclass
class _FakeSearchEngine:
    """Engine fake para simular retrieval sem MySQL/BM25 real."""

    canned_candidates: list[RetrievalCandidate]
    known_disciplines: frozenset[str]
    doc_chunks: list[dict[str, str]]

    @property
    def chunks(self) -> list[dict]:
        return [
            {"source": f"db:{c.discipline}/{i}", "text": c.text, "discipline": c.discipline}
            for i, c in enumerate(self.canned_candidates)
        ] + self.doc_chunks

    @property
    def discipline_ids(self) -> frozenset[str]:
        return self.known_disciplines

    def normalize_discipline(self, raw: str | None) -> str | None:
        if raw is None:
            return None
        raw = raw.strip()
        return raw if raw in self.known_disciplines else None

    def chunks_for_scope(self, discipline_filter: str | None):
        return list(self.chunks)

    def search_candidates(
        self,
        query: str,
        candidate_k: int = CANDIDATE_K,
        discipline_filter: str | None = None,
    ) -> list[RetrievalCandidate]:
        nd = self.normalize_discipline(discipline_filter)
        if nd is None:
            return list(self.canned_candidates)[: candidate_k]
        return [c for c in self.canned_candidates if c.discipline == nd][: candidate_k]


def _cand(raw: float, text: str, discipline: str = "python", source: str | None = None) -> RetrievalCandidate:
    source = source or f"db:{discipline}/chunk"
    return RetrievalCandidate(
        source=source,
        chunk_id=f"{discipline}:0",
        text=text,
        discipline=discipline,
        raw_score=raw,
        normalized_score=min(1.0, raw / 10.0),
    )


# --- Fase 1: hard stop sem base --------------------------------------------

def test_query_without_hits_does_not_call_llm():
    engine = _FakeSearchEngine(canned_candidates=[], known_disciplines=frozenset({"python"}), doc_chunks=[])
    cm = ContextManager(_make_settings(), engine)  # type: ignore[arg-type]

    result = cm.build_messages("como usar variavel em python")

    assert result.trace.decision == "hard_stop"
    assert result.trace.reason == "insufficient_context"
    # A última mensagem é a resposta pré-montada (não será enviada ao LLM).
    assert result.messages[-1]["role"] == "assistant"
    assert hard_stop_message("insufficient_context") in result.messages[-1]["content"]


def test_low_score_generates_insufficient_context():
    engine = _FakeSearchEngine(
        canned_candidates=[_cand(0.1, "texto qualquer")],
        known_disciplines=frozenset({"python"}),
        doc_chunks=[],
    )
    cm = ContextManager(_make_settings(), engine)  # type: ignore[arg-type]

    result = cm.build_messages("performance sql query")

    assert result.trace.reason == "insufficient_context"
    assert result.trace.confidence == "low"


# --- /content não injeta scope_chunks[:5] ----------------------------------

def test_slash_content_without_hits_hard_stops_instead_of_fallback():
    # Engine com chunks disponíveis no escopo (via chunks_for_scope) mas
    # SEM hits no search_candidates — antes, o fluxo injetava top-5 do escopo.
    chunks_in_db = [_cand(0.1, "texto muito fraco") for _ in range(8)]
    engine = _FakeSearchEngine(
        canned_candidates=chunks_in_db,
        known_disciplines=frozenset({"python"}),
        doc_chunks=[],
    )
    cm = ContextManager(_make_settings(), engine)  # type: ignore[arg-type]

    result = cm.build_messages("/content qualquer coisa estranha")

    assert result.trace.decision == "hard_stop", (
        "/content não deve mais injetar scope_chunks[:5] como fallback"
    )
    # system prompt deve ser o prompt base (sem anexos de chunk).
    system = result.messages[0]["content"]
    assert "base de conhecimento local" not in system.lower()


# --- /doc com silo doc funcionando -----------------------------------------

def test_slash_doc_injects_doc_chunks_when_available():
    doc_chunks = [
        {"source": "db:doc/a", "text": "documentação alpha", "discipline": "doc"},
        {"source": "db:doc/b", "text": "documentação beta", "discipline": "doc"},
    ]
    engine = _FakeSearchEngine(
        canned_candidates=[],
        known_disciplines=frozenset({"doc"}),
        doc_chunks=doc_chunks,
    )
    cm = ContextManager(_make_settings(), engine)  # type: ignore[arg-type]

    result = cm.build_messages("/doc como funciona /reload")

    assert result.trace.decision == "answer"
    system = result.messages[0]["content"]
    assert "db:doc/a" in system
    assert "db:doc/b" in system


def test_slash_doc_without_doc_silo_hard_stops():
    engine = _FakeSearchEngine(
        canned_candidates=[],
        known_disciplines=frozenset({"python"}),
        doc_chunks=[],
    )
    cm = ContextManager(_make_settings(), engine)  # type: ignore[arg-type]

    result = cm.build_messages("/doc o que é ACL")

    assert result.trace.decision == "hard_stop"
    assert result.trace.reason == "insufficient_context"


# --- Query especificada com hit bom gera resposta --------------------------

def test_aligned_query_produces_answer_path():
    chunk_text = (
        "sql select from tabela where filtro group by campo; performance "
        "melhora com índices corretos"
    )
    engine = _FakeSearchEngine(
        canned_candidates=[
            _cand(10.0, chunk_text, discipline="visualizacao-sql", source="db:visualizacao-sql/idx"),
            _cand(4.0, "outro texto", discipline="visualizacao-sql", source="db:visualizacao-sql/out"),
        ],
        known_disciplines=frozenset({"visualizacao-sql"}),
        doc_chunks=[],
    )
    cm = ContextManager(_make_settings(), engine)  # type: ignore[arg-type]

    result = cm.build_messages("/visualizacao-sql sql performance")

    assert result.trace.decision == "answer", f"got {result.trace.reason}"
    assert result.decision is not None
    assert result.decision.allow_generation is True


# --- Mode sempre strict nesta mitigação -------------------------------------

def test_mode_is_always_strict_without_flag():
    engine = _FakeSearchEngine(
        canned_candidates=[_cand(0.1, "fraco")],
        known_disciplines=frozenset({"python"}),
        doc_chunks=[],
    )
    cm = ContextManager(_make_settings(), engine)  # type: ignore[arg-type]

    result = cm.build_messages("/python como usar variavel")

    assert result.trace.mode == "strict"


# --- ACL_META distingue respostas --------------------------------------------

def test_trace_has_retrieval_trace_fields_on_hard_stop():
    engine = _FakeSearchEngine(
        canned_candidates=[_cand(5.0, "erro comum em api")],
        known_disciplines=frozenset({"python"}),
        doc_chunks=[],
    )
    cm = ContextManager(_make_settings(), engine)  # type: ignore[arg-type]

    result = cm.build_messages("erro api")

    assert result.trace.decision == "hard_stop"
    assert result.trace.reason == "vague_but_high_risk"
    assert result.trace.retrieval_trace is not None
    assert result.trace.retrieval_trace.llm_called is False
