"""Testes para GroupMemoryStore (Persistência SQLite, BM25 por canal, Recência e Isolamento)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from kernel.memory.group_memory import GroupMemoryStore


@pytest.fixture
def memory_store(tmp_path: Path) -> GroupMemoryStore:
    db_file = tmp_path / "group_memory_test.sqlite3"
    return GroupMemoryStore(db_file)


def test_record_and_get_recent_messages(memory_store: GroupMemoryStore) -> None:
    msg1 = memory_store.record_message(
        platform="whatsapp",
        channel_id="group-123@g.us",
        message_id="msg-1",
        user_id="user-a",
        sender_name="Alice",
        content="Olá a todos, quando é a prova de Python?",
    )
    assert msg1.id > 0
    assert msg1.content == "Olá a todos, quando é a prova de Python?"

    msg2 = memory_store.record_message(
        platform="whatsapp",
        channel_id="group-123@g.us",
        message_id="msg-2",
        user_id="user-b",
        sender_name="Bob",
        content="A prova de Python é na próxima terça!",
    )
    assert msg2.id > msg1.id

    recent = memory_store.get_recent_messages("whatsapp", "group-123@g.us", limit=10)
    assert len(recent) == 2
    assert recent[0].message_id == "msg-1"
    assert recent[1].message_id == "msg-2"


def test_batch_record_messages(memory_store: GroupMemoryStore) -> None:
    batch = [
        {
            "platform": "whatsapp",
            "channel_id": "group-456@g.us",
            "message_id": f"batch-{i}",
            "user_id": f"user-{i}",
            "sender_name": f"Aluno {i}",
            "content": f"Discussão sobre banco de dados parte {i}",
        }
        for i in range(10)
    ]
    inserted = memory_store.record_messages_batch(batch)
    assert inserted == 10
    assert memory_store.count_messages("whatsapp", "group-456@g.us") == 10


def test_bm25_historical_search_and_recency(memory_store: GroupMemoryStore) -> None:
    # Insere mensagens antigas e recentes
    memory_store.record_message(
        platform="whatsapp",
        channel_id="group-math@g.us",
        message_id="m-old",
        user_id="user-1",
        sender_name="Carlos",
        timestamp="2026-01-01T10:00:00Z",
        content="O trabalho sobre grafos e árvores binárias deve ser feito em C++.",
    )
    memory_store.record_message(
        platform="whatsapp",
        channel_id="group-math@g.us",
        message_id="m-new",
        user_id="user-2",
        sender_name="Daniela",
        timestamp="2026-08-15T10:00:00Z",
        content="O professor avisou que o trabalho sobre grafos foi adiado para sexta.",
    )
    memory_store.record_message(
        platform="whatsapp",
        channel_id="group-math@g.us",
        message_id="m-unrelated",
        user_id="user-3",
        sender_name="Eduardo",
        timestamp="2026-08-15T11:00:00Z",
        content="Alguém quer almoçar no bandejão hoje?",
    )

    results = memory_store.search_historical(
        "whatsapp", "group-math@g.us", "trabalho sobre grafos", top_k=5, recency_weight=0.5
    )
    assert len(results) >= 2
    assert results[0].message_id in ("m-new", "m-old")
    # A mensagem mais recente tem maior recency_factor
    new_res = next(r for r in results if r.message_id == "m-new")
    old_res = next(r for r in results if r.message_id == "m-old")
    assert new_res.recency_factor >= old_res.recency_factor


def test_strict_group_isolation(memory_store: GroupMemoryStore) -> None:
    memory_store.record_message(
        platform="whatsapp",
        channel_id="group-secret-A@g.us",
        message_id="sec-1",
        user_id="alice",
        sender_name="Alice",
        content="Código secreto do projeto alfa: 998877",
    )
    memory_store.record_message(
        platform="whatsapp",
        channel_id="group-public-B@g.us",
        message_id="pub-1",
        user_id="bob",
        sender_name="Bob",
        content="Bom dia turma!",
    )

    # Busca no grupo B não pode vazar nada do grupo A
    res_b = memory_store.search_historical(
        "whatsapp", "group-public-B@g.us", "código secreto alfa"
    )
    assert len(res_b) == 0

    # Busca no grupo A encontra
    res_a = memory_store.search_historical(
        "whatsapp", "group-secret-A@g.us", "código secreto alfa"
    )
    assert len(res_a) == 1
    assert res_a[0].message_id == "sec-1"


def test_delete_group_memory_isolated(memory_store: GroupMemoryStore) -> None:
    memory_store.record_message(
        platform="whatsapp",
        channel_id="group-to-delete@g.us",
        message_id="del-1",
        user_id="u1",
        content="Mensagem a ser apagada",
    )
    memory_store.record_message(
        platform="whatsapp",
        channel_id="group-to-keep@g.us",
        message_id="keep-1",
        user_id="u2",
        content="Mensagem a ser preservada",
    )

    del_res = memory_store.delete_group_memory("whatsapp", "group-to-delete@g.us")
    assert del_res["deleted_messages"] == 1
    assert memory_store.count_messages("whatsapp", "group-to-delete@g.us") == 0
    assert memory_store.count_messages("whatsapp", "group-to-keep@g.us") == 1


def test_group_state_persistence(memory_store: GroupMemoryStore) -> None:
    st1 = memory_store.get_group_state("whatsapp", "group-intro@g.us")
    assert st1["introduction_sent"] is False
    assert st1["introduction_sent_at"] is None

    memory_store.set_group_state("whatsapp", "group-intro@g.us", True)
    st2 = memory_store.get_group_state("whatsapp", "group-intro@g.us")
    assert st2["introduction_sent"] is True
    assert st2["introduction_sent_at"] is not None
