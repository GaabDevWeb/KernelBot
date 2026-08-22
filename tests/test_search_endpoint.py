from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.factory import create_app
from app.state import AppServices
from kernel.rag.retrieval import RetrievalCandidate


@dataclass
class SettingsStub:
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


class ContextManagerStub:
    settings = SettingsStub()


class SearchEngineStub:
    def search_candidates(self, *_args, **_kwargs):
        return [
            RetrievalCandidate(
                source="db:sql/aula",
                chunk_id="sql:0",
                text="Normalização reduz redundância.",
                discipline="sql",
                raw_score=4.0,
                normalized_score=1.0,
                matched_terms=("normalização",),
            )
        ]


def test_search_returns_retrieval_contract() -> None:
    services = AppServices(
        search_engine=SearchEngineStub(),  # type: ignore[arg-type]
        context_manager=ContextManagerStub(),  # type: ignore[arg-type]
        chat_provider=None,  # type: ignore[arg-type]
        pinned_store=None,  # type: ignore[arg-type]
    )
    response = TestClient(create_app(services)).post(
        "/search", json={"message": "normalização SQL", "top_k": 1}
    )

    assert response.status_code == 200
    assert response.json()["candidates"][0]["source"] == "db:sql/aula"
