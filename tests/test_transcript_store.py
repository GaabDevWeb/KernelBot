"""Testes da janela deslizante de transcript por chave v1."""

from kernel.memory.transcript_store import TranscriptStore


def test_append_pair_beyond_max_turns_keeps_last_n_pairs() -> None:
    store = TranscriptStore()
    key = "discord:u1:chan1"
    for i in range(5):
        store.append_pair(key, f"pergunta {i}", f"resposta {i}", max_turns=2)

    transcript = store.get(key)
    assert len(transcript) == 4
    assert transcript[0] == {"role": "user", "content": "pergunta 3"}
    assert transcript[1] == {"role": "assistant", "content": "resposta 3"}
    assert transcript[2] == {"role": "user", "content": "pergunta 4"}
    assert transcript[3] == {"role": "assistant", "content": "resposta 4"}


def test_get_missing_key_returns_empty_list() -> None:
    store = TranscriptStore()
    assert store.get("chave-inexistente") == []


def test_clear_removes_transcript() -> None:
    store = TranscriptStore()
    key = "discord:u1:chan1"
    store.append_pair(key, "pergunta", "resposta", max_turns=2)
    assert store.get(key) != []

    store.clear(key)
    assert store.get(key) == []


def test_append_pair_is_noop_with_none_key_or_empty_messages() -> None:
    store = TranscriptStore()
    store.append_pair(None, "pergunta", "resposta", max_turns=2)
    store.append_pair("chave", "", "resposta", max_turns=2)
    store.append_pair("chave", "pergunta", "", max_turns=2)

    assert store.get(None) == []
    assert store.get("chave") == []
