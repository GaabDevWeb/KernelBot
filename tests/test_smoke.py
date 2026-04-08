"""Smoke tests sem importar main (evita observer global na pasta content do repo)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.factory import create_app
from app.state import AppServices
from core.config import Settings
from engine.chat_provider import ChatProvider
from engine.context import ContextManager
from engine.pinned_store import PinnedSessionStore
from engine.search import SearchEngine

_PINNED_KW = {
    "pinned_max_turns": 5,
    "pinned_max_chars": 50_000,
    "pinned_weak_score": 0.4,
}


class _NoopObserver:
    def stop(self) -> None:
        pass

    def join(self) -> None:
        pass


def _settings_with_tmp_content(tmp_path: Path) -> Settings:
    content = tmp_path / "content"
    content.mkdir()
    (content / "note.md").write_text("# Title\n\nhello world keyword\n", encoding="utf-8")
    return Settings(
        openrouter_api_key="test-key",
        project_root=tmp_path,
        content_dir=content,
        bm25_score_threshold=0.7,
        global_context_mode="geral",
        openrouter_base="https://openrouter.ai/api/v1/chat/completions",
        models=("model-a",),
        system_prompt_geral="System.",
        http_timeout=60.0,
        **_PINNED_KW,
    )


def _app_services(settings: Settings, engine: SearchEngine) -> AppServices:
    ps = PinnedSessionStore()
    return AppServices(
        search_engine=engine,
        context_manager=ContextManager(settings, engine, pinned_store=ps),
        chat_provider=ChatProvider(settings),
        observer=_NoopObserver(),
        pinned_store=ps,
    )


def test_search_engine_finds_chunk(tmp_path: Path) -> None:
    settings = _settings_with_tmp_content(tmp_path)
    engine = SearchEngine(
        settings.content_dir,
        settings.bm25_score_threshold,
        settings.global_context_mode,
    )
    assert len(engine.chunks) >= 1
    hits = engine.search("keyword")
    assert len(hits) >= 1
    assert hits[0]["source"] == "note.md"


def test_get_home_returns_html(tmp_path: Path) -> None:
    settings = _settings_with_tmp_content(tmp_path)
    engine = SearchEngine(
        settings.content_dir,
        settings.bm25_score_threshold,
        settings.global_context_mode,
    )
    services = _app_services(settings, engine)
    client = TestClient(create_app(services))
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    body = response.text
    assert 'type="module"' in body
    assert "/src/main.js" in body
    assert "/assets/css/theme.css" in body


def test_static_frontend_assets(tmp_path: Path) -> None:
    settings = _settings_with_tmp_content(tmp_path)
    engine = SearchEngine(
        settings.content_dir,
        settings.bm25_score_threshold,
        settings.global_context_mode,
    )
    services = _app_services(settings, engine)
    client = TestClient(create_app(services))
    css = client.get("/assets/css/theme.css")
    assert css.status_code == 200
    assert "text/css" in css.headers.get("content-type", "")
    main_js = client.get("/src/main.js")
    assert main_js.status_code == 200
    assert "javascript" in main_js.headers.get("content-type", "").lower()


def test_chat_empty_message_400(tmp_path: Path) -> None:
    settings = _settings_with_tmp_content(tmp_path)
    engine = SearchEngine(
        settings.content_dir,
        settings.bm25_score_threshold,
        settings.global_context_mode,
    )
    services = _app_services(settings, engine)
    client = TestClient(create_app(services))
    response = client.post("/chat", json={"message": "   "})
    assert response.status_code == 400


def test_search_discipline_filter_no_cross_silo_leak(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    (content / "python").mkdir()
    (content / "sql-silo").mkdir()
    (content / "python" / "a.md").write_text("# A\n\nalphauniquepytoken\n", encoding="utf-8")
    (content / "sql-silo" / "b.md").write_text("# B\n\nbetauniquesqltoken\n", encoding="utf-8")
    engine = SearchEngine(content, 0.0, "all")
    py_hits = engine.search("alphauniquepytoken", discipline_filter="python")
    assert py_hits
    assert all(h["discipline"] == "python" for h in py_hits)
    assert not engine.search("betauniquesqltoken", discipline_filter="python")


def test_normalize_discipline_rejects_unsafe_and_unknown(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    (content / "python").mkdir()
    (content / "note.md").write_text("# x\n\ny\n", encoding="utf-8")
    engine = SearchEngine(content, 0.7, "geral")
    assert engine.normalize_discipline("..") is None
    assert engine.normalize_discipline("foo/bar") is None
    assert engine.normalize_discipline("") is None
    assert engine.normalize_discipline("nao_existe") is None


def test_global_context_geral_only_root_and_geral_folder(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    (content / "python").mkdir()
    (content / "python" / "a.md").write_text("# A\n\nonlyinpython\n", encoding="utf-8")
    engine = SearchEngine(content, 0.0, "geral")
    assert engine.search("onlyinpython") == []


def test_doc_prefix_injects_only_doc_silo(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    (content / "doc").mkdir()
    (content / "python").mkdir()
    (content / "doc" / "manual.md").write_text("# M\n\nONLY_DOC_SILO_MARK\n", encoding="utf-8")
    (content / "python" / "lesson.md").write_text("# L\n\nONLY_PY_SILO_MARK\n", encoding="utf-8")
    settings = Settings(
        openrouter_api_key="test-key",
        project_root=tmp_path,
        content_dir=content,
        bm25_score_threshold=0.7,
        global_context_mode="geral",
        openrouter_base="https://openrouter.ai/api/v1/chat/completions",
        models=("model-a",),
        system_prompt_geral="System.",
        http_timeout=60.0,
        **_PINNED_KW,
    )
    engine = SearchEngine(content, 0.7, "geral")
    cm = ContextManager(settings, engine)
    built = cm.build_messages("/doc resumo")
    messages = built.messages
    system = messages[0]["content"]
    assert "ONLY_DOC_SILO_MARK" in system
    assert "ONLY_PY_SILO_MARK" not in system
    assert messages[1]["content"] == "resumo"
    assert built.trace.label == "Documentação (doc)"
    assert "doc/manual.md" in built.trace.sources


def test_python_prefix_does_not_match_inline(tmp_path: Path) -> None:
    """`/pythonfoo` não é comando; não deve forçar silo python."""
    content = tmp_path / "content"
    content.mkdir()
    (content / "python").mkdir()
    (content / "python" / "a.md").write_text("# A\n\npytok\n", encoding="utf-8")
    settings = Settings(
        openrouter_api_key="test-key",
        project_root=tmp_path,
        content_dir=content,
        bm25_score_threshold=0.0,
        global_context_mode="geral",
        openrouter_base="https://openrouter.ai/api/v1/chat/completions",
        models=("model-a",),
        system_prompt_geral="System.",
        http_timeout=60.0,
        **_PINNED_KW,
    )
    engine = SearchEngine(content, 0.0, "geral")
    cm = ContextManager(settings, engine)
    built = cm.build_messages("/pythonfoo pytok")
    messages = built.messages
    assert messages[0]["content"] == "System."
    assert messages[1]["content"] == "/pythonfoo pytok"
    assert built.trace.label == "Assistente geral"
    assert built.trace.sources == ()


def test_discipline_prefix_forces_rag_in_silo(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    (content / "python").mkdir()
    (content / "python" / "a.md").write_text("# A\n\nuniqueprefixragtoken\n", encoding="utf-8")
    settings = Settings(
        openrouter_api_key="test-key",
        project_root=tmp_path,
        content_dir=content,
        bm25_score_threshold=0.0,
        global_context_mode="geral",
        openrouter_base="https://openrouter.ai/api/v1/chat/completions",
        models=("model-a",),
        system_prompt_geral="System.",
        http_timeout=60.0,
        **_PINNED_KW,
    )
    engine = SearchEngine(content, 0.0, "geral")
    cm = ContextManager(settings, engine)
    built = cm.build_messages("/python uniqueprefixragtoken")
    messages = built.messages
    assert "uniqueprefixragtoken" in messages[0]["content"]
    assert messages[1]["content"] == "uniqueprefixragtoken"
    assert built.trace.label == "Python"
    assert "python/a.md" in built.trace.sources


def test_chat_discipline_non_string_400(tmp_path: Path) -> None:
    settings = _settings_with_tmp_content(tmp_path)
    engine = SearchEngine(
        settings.content_dir,
        settings.bm25_score_threshold,
        settings.global_context_mode,
    )
    services = _app_services(settings, engine)
    client = TestClient(create_app(services))
    response = client.post("/chat", json={"message": "olá", "discipline": ["python"]})
    assert response.status_code == 400


def test_chat_session_id_invalid_400(tmp_path: Path) -> None:
    settings = _settings_with_tmp_content(tmp_path)
    engine = SearchEngine(
        settings.content_dir,
        settings.bm25_score_threshold,
        settings.global_context_mode,
    )
    services = _app_services(settings, engine)
    client = TestClient(create_app(services))
    r = client.post("/chat", json={"message": "olá", "session_id": "curto"})
    assert r.status_code == 400
    r2 = client.post("/chat", json={"message": "olá", "session_id": ["x"]})
    assert r2.status_code == 400


def test_pinned_follow_up_without_bm25_hits(tmp_path: Path) -> None:
    """Pergunta de acompanhamento sem hits BM25 reutiliza chunks fixados na sessão."""
    content = tmp_path / "content"
    content.mkdir()
    (content / "python").mkdir()
    mark = "PINNED_UNIQUE_LESSON_BODY"
    (content / "python" / "aula-15.md").write_text(
        f"# Título\n\n{mark} e notas sobre avaliação.\n",
        encoding="utf-8",
    )
    settings = Settings(
        openrouter_api_key="k",
        project_root=tmp_path,
        content_dir=content,
        bm25_score_threshold=0.0,
        global_context_mode="geral",
        openrouter_base="https://x",
        models=("m",),
        system_prompt_geral="Sys.",
        http_timeout=60.0,
        **_PINNED_KW,
    )
    engine = SearchEngine(content, 0.0, "geral")
    store = PinnedSessionStore()
    cm = ContextManager(settings, engine, pinned_store=store)
    sid = "sess_test_01"
    first = cm.build_messages(f"/python resumo {mark}", session_id=sid)
    assert mark in first.messages[0]["content"]
    assert store.get(sid) is not None
    second = cm.build_messages("zzzzvoidquerynotincorpus", session_id=sid)
    assert mark in second.messages[0]["content"]
    assert "discutindo o material fixado" in second.messages[0]["content"].lower()
    assert second.trace.pinned_active is True


def test_reset_clears_pinned_session(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    (content / "python").mkdir()
    (content / "python" / "a.md").write_text("# A\n\nresettesttoken\n", encoding="utf-8")
    settings = Settings(
        openrouter_api_key="k",
        project_root=tmp_path,
        content_dir=content,
        bm25_score_threshold=0.0,
        global_context_mode="geral",
        openrouter_base="https://x",
        models=("m",),
        system_prompt_geral="Sys.",
        http_timeout=60.0,
        **_PINNED_KW,
    )
    engine = SearchEngine(content, 0.0, "geral")
    store = PinnedSessionStore()
    cm = ContextManager(settings, engine, pinned_store=store)
    sid = "sess_reset_01"
    cm.build_messages("/python resettesttoken", session_id=sid)
    assert store.get(sid) is not None
    cm.build_messages("/reset continuar", session_id=sid)
    assert store.get(sid) is None
