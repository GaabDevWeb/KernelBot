"""Testes de isolamento de chave de memória/pin."""

from kernel.memory.session_key import memory_session_key


def test_memory_session_key_isolates_users() -> None:
    a = memory_session_key("discord", "u1", "sess_abcd12")
    b = memory_session_key("discord", "u2", "sess_abcd12")
    c = memory_session_key("telegram", "u1", "sess_abcd12")
    assert a != b
    assert a != c
    assert a == "discord:u1:sess_abcd12"


def test_memory_session_key_none_without_session() -> None:
    assert memory_session_key("cli", "u1", None) is None
