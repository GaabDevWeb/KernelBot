"""Testes da detecção de intents temporais (sem LLM)."""

from __future__ import annotations

import pytest

from kernel.context.intent import detect_temporal_intent


@pytest.mark.parametrize(
    "query",
    [
        "Que dia é hoje?",
        "que dia e hoje",
        "Hoje é que dia?",
        "Que horas são?",
        "que horas sao agora",
        "Qual é a data de hoje?",
        "Que dia da semana é amanhã?",
        "qual a data atual?",
    ],
)
def test_time_fact_questions(query):
    intent = detect_temporal_intent(query)
    assert intent is not None and intent.kind == "time_fact"


@pytest.mark.parametrize(
    "query",
    [
        "Quando é a próxima prova?",
        "quando e a proxima avaliacao",
        "Quantos dias faltam para a AT de Banco de Dados?",
        "quantos dias falta pra entrega?",
        "Qual é a próxima avaliação?",
        "O que temos essa semana?",
        "Tem prova amanhã?",
        "tem entrega essa semana?",
        "O que aconteceu ontem?",
        "Qual é a próxima entrega?",
        "próximo seminário é quando?",
        "quando vai ser a prova de python?",
    ],
)
def test_calendar_fact_questions(query):
    intent = detect_temporal_intent(query)
    assert intent is not None and intent.kind == "calendar_fact"


@pytest.mark.parametrize(
    "query",
    [
        "O que é um JOIN em SQL?",
        "Como funciona um loop for em Python?",
        "me explica normalização de banco de dados",
        "",
        "   ",
        "hoje aprendi sobre grafos",  # menciona 'hoje' mas não pergunta a data
    ],
)
def test_non_temporal_questions_return_none(query):
    assert detect_temporal_intent(query) is None
