"""Testes para IdempotencyStore no Kernel."""

from __future__ import annotations

import time

import pytest

from kernel.memory.idempotency import IdempotencyStore


def test_idempotency_claim_and_complete() -> None:
    store = IdempotencyStore(default_ttl_seconds=5)
    key = "whatsapp:group-1:msg-123"

    # Primeira chamada: claim bem sucedido (MISS)
    can_proceed, rec = store.claim(key)
    assert can_proceed is True
    assert rec is None

    # Segunda chamada concorrente enquanto em processamento (HIT)
    can_proceed_2, rec_2 = store.claim(key)
    assert can_proceed_2 is False
    assert rec_2 is not None
    assert rec_2.status == "processing"

    # Completa a chamada com resposta
    fake_response = {"text": "Resposta processada", "status": "ok"}
    store.complete(key, fake_response)

    # Terceira chamada: HIT com status completed
    can_proceed_3, rec_3 = store.claim(key)
    assert can_proceed_3 is False
    assert rec_3 is not None
    assert rec_3.status == "completed"
    assert rec_3.response_data == fake_response


def test_idempotency_fail_allows_retry() -> None:
    store = IdempotencyStore(default_ttl_seconds=5)
    key = "whatsapp:group-1:msg-error"

    can_proceed, _ = store.claim(key)
    assert can_proceed is True

    # Falha na execução (ex: LLM down) -> fail remove a chave
    store.fail(key)

    # Novo retry imediato pode prosseguir
    can_retry, rec = store.claim(key)
    assert can_retry is True
    assert rec is None


def test_idempotency_ttl_expiration() -> None:
    store = IdempotencyStore(default_ttl_seconds=1)
    key = "whatsapp:group-1:msg-ttl"

    store.claim(key, ttl_seconds=1)
    store.complete(key, {"answer": "old"}, ttl_seconds=1)

    time.sleep(1.1)

    # Após expiração, a chave pode ser reservada novamente
    can_claim, rec = store.claim(key)
    assert can_claim is True
