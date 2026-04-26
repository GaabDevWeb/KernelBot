"""Testes do ChatProvider — streaming com hard stop e sanity check pós-geração.

O objetivo é validar, sem chamar a OpenRouter de verdade:

- Quando `trace.decision == "hard_stop"`, nenhuma chamada HTTP é feita.
- A resposta streamada é exatamente `hard_stop_message(reason)`.
- O meta inclui `llm_called=False`, `reason` e `confidence`.
- Sanity check pós-geração troca o desfecho para `post_generation_misalignment`
  quando a resposta falha no check.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import Settings
from engine.chat_provider import ChatProvider
from engine.context import ContextTrace, hard_stop_message
from engine.retrieval import (
    CANDIDATE_K,
    RetrievalCandidate,
    RetrievalDecision,
    RetrievalTrace,
)


def _make_settings() -> Settings:
    return Settings(  # type: ignore[arg-type]
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


async def _drain(agen):
    out: list[str] = []
    async for piece in agen:
        out.append(piece)
    return out


def _parse_meta(lines: list[str]) -> dict:
    for line in lines:
        if "[ACL_META]" in line:
            payload = line.split("[ACL_META]", 1)[1].strip()
            return json.loads(payload)
    raise AssertionError("Nenhum [ACL_META] encontrado no stream")


def _collect_body(result: list[str]) -> str:
    pieces: list[str] = []
    for line in result:
        if not line.startswith("data: "):
            continue
        if "[DONE]" in line or "[ACL_META]" in line:
            continue
        payload = line[len("data: "):].rstrip("\n").replace("\\n", "\n")
        pieces.append(payload)
    return "".join(pieces)


def test_hard_stop_stream_does_not_call_http():
    provider = ChatProvider(_make_settings())
    trace = ContextTrace(
        label="Base geral",
        sources=(),
        mode="strict",
        decision="hard_stop",
        reason="insufficient_context",
        confidence="low",
    )
    messages = [
        {"role": "system", "content": "SYSTEM_PROMPT_BASE"},
        {"role": "user", "content": "qualquer coisa"},
        {"role": "assistant", "content": hard_stop_message("insufficient_context")},
    ]

    # Se o provider tentar HTTP real, httpx.AsyncClient falhará sobre DNS/conexão,
    # mas a rota hard stop NÃO deve acioná-lo. Passamos um base URL inválido
    # apenas como canary — se a request rolar, esse teste quebra com timeout.
    result = asyncio.run(_drain(provider.stream_response(messages, trace=trace)))

    assert any("[DONE]" in line for line in result)
    meta = _parse_meta(result)
    assert meta["decision"] == "hard_stop"
    assert meta["reason"] == "insufficient_context"
    assert meta["llm_called"] is False

    body = _collect_body(result)
    assert "Não encontrei informação suficiente" in body


def test_hard_stop_uses_underspecified_message():
    provider = ChatProvider(_make_settings())
    trace = ContextTrace(
        label="Base geral",
        sources=(),
        mode="strict",
        decision="hard_stop",
        reason="underspecified_query",
        confidence="low",
    )
    messages = [
        {"role": "system", "content": "SYSTEM_PROMPT_BASE"},
        {"role": "user", "content": "performance"},
        {"role": "assistant", "content": hard_stop_message("underspecified_query")},
    ]

    result = asyncio.run(_drain(provider.stream_response(messages, trace=trace)))
    body = _collect_body(result)
    assert "vaga para responder com segurança" in body
    assert "[tecnologia] + [problema] + [contexto]" in body


def test_hard_stop_vague_but_high_risk_has_specific_ux():
    provider = ChatProvider(_make_settings())
    trace = ContextTrace(
        label="Base geral",
        sources=(),
        mode="strict",
        decision="hard_stop",
        reason="vague_but_high_risk",
        confidence="low",
    )
    messages = [
        {"role": "system", "content": "SYSTEM_PROMPT_BASE"},
        {"role": "user", "content": "erro api"},
        {"role": "assistant", "content": hard_stop_message("vague_but_high_risk")},
    ]

    result = asyncio.run(_drain(provider.stream_response(messages, trace=trace)))
    body = _collect_body(result)
    assert "várias interpretações" in body
    assert "[tecnologia] + [problema] + [contexto]" in body


def test_meta_carries_mode_and_confidence_on_answer_path_before_http():
    """Primeiro meta emitido no path de geração traz llm_called=True."""
    provider = ChatProvider(_make_settings())
    trace = ContextTrace(
        label="Python",
        sources=("db:python/a",),
        mode="strict",
        decision="answer",
        reason="ok",
        confidence="high",
    )
    messages = [
        {"role": "system", "content": "SYSTEM_PROMPT_BASE"},
        {"role": "user", "content": "pergunta aleatória"},
    ]

    # Interrompe o gerador após primeiro meta para evitar HTTP.
    async def first_meta_only():
        async for piece in provider.stream_response(messages, trace=trace):
            if "[ACL_META]" in piece:
                return piece
        return None

    first = asyncio.run(first_meta_only())
    assert first is not None
    meta = _parse_meta([first])
    assert meta["mode"] == "strict"
    assert meta["confidence"] == "high"
    assert meta["llm_called"] is True


def test_post_generation_override_flags_answer_without_any_informative_term():
    """Se a resposta não usa nenhum termo informativo, o sanity check dispara."""
    # Simula internamente o helper, já que não queremos chamar HTTP.
    from engine.retrieval import post_generation_flags

    cand = RetrievalCandidate(
        source="db:python/a",
        chunk_id="python:0",
        text="variaveis em python armazenam valores",
        discipline="python",
        raw_score=5.0,
        normalized_score=0.5,
    )
    flags = post_generation_flags(
        "Resposta que ignora totalmente a pergunta e só fala sobre culinária.",
        ["variavel", "python"],
        [cand],
    )
    assert "missing_informative_terms" in flags
