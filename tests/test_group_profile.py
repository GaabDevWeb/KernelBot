"""Testes para GroupProfile, GroupProfileAnalyzer e barreira ética Opinião ≠ Fato."""

from __future__ import annotations

import pytest

from kernel.memory.group_profile import (
    GroupProfile,
    GroupProfileAnalyzer,
)


def test_group_profile_extraction_and_topics() -> None:
    messages = [
        {"content": "Alguém conseguiu resolver a list comprehension em Python?", "timestamp": "2026-08-01T10:00:00Z"},
        {"content": "Sim, usa lambda e map com python puro kkk", "timestamp": "2026-08-01T10:05:00Z"},
        {"content": "Quando é a prova de banco de dados e SQL?", "timestamp": "2026-08-02T11:00:00Z"},
        {"content": "A prova vai cair select e join com mysql", "timestamp": "2026-08-02T11:05:00Z"},
        {"content": "O prof Silva explica muito bem, adorei a didática!", "timestamp": "2026-08-03T14:00:00Z"},
        {"content": "Sim, o prof Silva é muito didático e gente boa", "timestamp": "2026-08-03T14:10:00Z"},
    ]

    profile = GroupProfileAnalyzer.extract_profile("whatsapp", "group-turma-a@g.us", messages)

    assert profile.platform == "whatsapp"
    assert profile.channel_id == "group-turma-a@g.us"
    assert "Python" in profile.common_topics or "Banco de Dados" in profile.common_topics
    assert profile.communication_style in ("informal", "equilibrado")

    # Verifica percepção sobre o professor
    assert "Professor Silva" in profile.social_context
    silva_data = profile.social_context["Professor Silva"]
    assert silva_data["sentiment"] == "positive"
    assert silva_data["confidence"] >= 0.5
    assert silva_data["evidence_count"] >= 2


def test_ethical_boundary_prompt_block() -> None:
    profile = GroupProfile(
        platform="whatsapp",
        channel_id="group-turma-b@g.us",
        updated_at="2026-08-16T12:00:00Z",
        communication_style="informal",
        common_topics=["Python", "Banco de Dados"],
        recurring_questions=["Datas de avaliações"],
        social_context={
            "Professor Mendes": {
                "sentiment": "negative",
                "confidence": 0.85,
                "evidence_count": 15,
                "themes": ["provas difíceis", "didática"],
            }
        },
        sentiment_history=[
            {"period": "2026-08", "target": "Professor Mendes", "sentiment": "negative", "confidence": 0.85, "evidence_count": 15}
        ],
    )

    block = profile.prompt_block()
    assert "Contexto social e dinâmico da turma" in block
    assert "Professor Mendes" in block
    assert "IMPORTANTE — HIERARQUIA DE VERDADE" in block
    assert "NÃO são fatos institucionais nem verdades objetivas" in block


def test_group_profile_serialization() -> None:
    profile = GroupProfile(
        platform="whatsapp",
        channel_id="g1",
        updated_at="2026-08-16T10:00:00Z",
        communication_style="informal",
        common_topics=["Python"],
    )
    p_dict = profile.to_dict()
    restored = GroupProfile.from_dict(p_dict)
    assert restored.channel_id == "g1"
    assert restored.communication_style == "informal"
    assert restored.common_topics == ["Python"]
