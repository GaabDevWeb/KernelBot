"""Testes Ops Center P1 — Conhecimento."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.factory import create_app
from app.state import AppServices
from kernel.comms.store import reset_comms_store_for_tests
from kernel.orchestrator.context import BuildMessagesResult, ContextTrace
from kernel.rag.retrieval import RetrievalCandidate, RetrievalDecision, RetrievalTrace
from kernel.trace import reset_trace_bus_for_tests
from kernel.users.store import reset_users_store_for_tests

TOKEN = "knowledge-p1-token"


@dataclass
class SettingsStub:
    catalog_enabled: bool = False
    retrieval_candidate_k: int = 8
    retrieval_min_score: float = 1.5
    retrieval_min_score_margin: float = 0.15
    retrieval_min_coverage: float = 0.34
    retrieval_min_coverage_weighted: float = 0.34
    retrieval_min_terms: int = 2
    retrieval_top_k: int = 4
    retrieval_max_chunks_per_source: int = 2
    retrieval_mode: str = "strict"
    disambiguation_enabled: bool = False
    grounding_policy: str = "anchored"
    llm_provider: str = "openrouter"
    cursor_model: str = "composer-2.5"
    cursor_api_key: str = ""
    openrouter_api_key: str = "x"
    models: tuple[str, ...] = ("m1",)
    global_context_mode: str = "geral"
    db_host: str = ""
    db_name: str = ""
    db_user: str = ""
    db_password: str = ""
    db_port: int = 3306
    project_root: object = None
    chunk_words: int = 500
    system_prompt_geral: str = "sys"
    catalog_router_prompt: str = ""
    pinned_max_chars: int = 4000
    chat_history_max_turns: int = 4
    chat_history_max_chars: int = 4000

    def __post_init__(self) -> None:
        if self.project_root is None:
            self.project_root = Path(".").resolve()


class ContextManagerStub:
    settings = SettingsStub()

    def __init__(self) -> None:
        self._keys: frozenset[str] = frozenset()

    def refresh_indexed_lesson_keys(self, keys: frozenset[str]) -> None:
        self._keys = keys

    def build_messages(
        self,
        message,
        discipline_filter=None,
        session_id=None,
        conversation_history=None,
        **_kwargs,
    ):
        cand = RetrievalCandidate(
            source="db:python/aula-01",
            chunk_id="python:0",
            text="Listas e dicionários em Python.",
            discipline="python",
            raw_score=3.5,
            normalized_score=1.0,
            matched_terms=("python",),
        )
        trace_r = RetrievalTrace(
            query=message,
            normalized_query=(message or "").lower(),
            informative_terms=("python",),
            mode="strict",
            top_score=3.5,
            second_score=1.0,
            score_margin=2.5,
            coverage=0.5,
            decision="answer",
            reason="ok",
        )
        decision = RetrievalDecision(
            allow_generation=True,
            reason="ok",
            confidence="high",
            selected_candidates=(cand,),
            trace=trace_r,
        )
        ctx = ContextTrace(
            label="Python",
            sources=("db:python/aula-01",),
            confidence="high",
            decision="answer",
            reason="ok",
        )
        return BuildMessagesResult(
            messages=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": message},
            ],
            trace=ctx,
            decision=decision,
            candidates_considered=(cand,),
            effective_discipline=discipline_filter or "python",
        )


class SearchEngineStub:
    chunks = [
        {
            "text": "Listas e dicionários em Python.",
            "source": "db:python/aula-01",
            "discipline": "python",
        },
        {
            "text": "Wiki intro.",
            "source": "db:doc/01-visao",
            "discipline": "doc",
        },
    ]
    discipline_ids = frozenset({"python", "doc"})

    def search_candidates(self, query, candidate_k=8, discipline_filter=None):
        return [
            RetrievalCandidate(
                source="db:python/aula-01",
                chunk_id="python:0",
                text="Listas e dicionários em Python.",
                discipline="python",
                raw_score=4.0,
                normalized_score=1.0,
                matched_terms=("python",),
            )
        ]

    def normalize_discipline(self, raw):
        if not raw:
            return None
        s = str(raw).strip()
        return s if s in self.discipline_ids else None

    def rebuild(self) -> None:
        return None


def _make_app():
    services = AppServices(
        search_engine=SearchEngineStub(),  # type: ignore[arg-type]
        context_manager=ContextManagerStub(),  # type: ignore[arg-type]
        chat_provider=SimpleNamespace(),  # type: ignore[arg-type]
        pinned_store=SimpleNamespace(get=lambda *_: None, clear=lambda *_: None),  # type: ignore[arg-type]
    )
    return create_app(services)


def test_knowledge_ops_routes_authenticated(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ACL_INTERNAL_BEARER_TOKEN", TOKEN)
    monkeypatch.setenv("ACL_USERS_DB_PATH", str(tmp_path / "users.sqlite3"))
    monkeypatch.setenv("ACL_COMM_DB_PATH", str(tmp_path / "comms.sqlite3"))
    monkeypatch.setenv("ACL_TRACE_DB_PATH", str(tmp_path / "traces.sqlite3"))
    monkeypatch.delenv("ENV", raising=False)
    reset_trace_bus_for_tests()
    reset_comms_store_for_tests()
    reset_users_store_for_tests()

    app = _make_app()
    with TestClient(app) as client:
        denied = client.get("/ops/knowledge/docs", follow_redirects=False)
        assert denied.status_code == 303

        login = client.post("/ops/login", data={"token": TOKEN}, follow_redirects=False)
        assert login.status_code == 303

        for path in (
            "/ops/knowledge/docs",
            "/ops/knowledge/search",
            "/ops/knowledge/rag",
            "/ops/knowledge/reindex",
        ):
            r = client.get(path)
            assert r.status_code == 200, path

        search = client.get("/ops/knowledge/search?q=python&mode=bm25")
        assert search.status_code == 200
        assert b"python" in search.content.lower() or b"aula-01" in search.content

        hybrid = client.get("/ops/knowledge/search?q=python&mode=hybrid")
        assert hybrid.status_code == 200

        full = client.get("/ops/knowledge/search?q=python&mode=full")
        assert full.status_code == 200

        rag = client.get("/ops/knowledge/rag?q=o+que+e+lista")
        assert rag.status_code == 200
        assert b"RAG Explorer" in rag.content or b"processada" in rag.content.lower()

        reindex = client.post(
            "/ops/knowledge/reindex",
            data={"scope": "all", "discipline": "", "document": "", "ingest_disk": ""},
        )
        assert reindex.status_code == 200
        assert b"rebuild_bm25" in reindex.content

        docs = client.get("/ops/knowledge/docs")
        assert docs.status_code == 200
        assert b"python" in docs.content.lower() or b"aula-01" in docs.content

    reset_users_store_for_tests()
    reset_comms_store_for_tests()
    reset_trace_bus_for_tests()


def test_list_documents_from_ram_chunks(monkeypatch):
    from kernel.knowledge import ops as knowledge_ops

    monkeypatch.setattr(knowledge_ops, "fetch_db_document_meta", lambda _s: [])
    services = AppServices(
        search_engine=SearchEngineStub(),  # type: ignore[arg-type]
        context_manager=ContextManagerStub(),  # type: ignore[arg-type]
        chat_provider=SimpleNamespace(),  # type: ignore[arg-type]
        pinned_store=SimpleNamespace(),  # type: ignore[arg-type]
    )
    listing = knowledge_ops.list_documents(services, q="python")
    assert listing["total"] >= 1
    assert listing["documents"][0]["discipline"] == "python"
    assert listing["documents"][0]["chunks"] >= 1
