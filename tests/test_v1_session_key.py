"""Testes de isolamento da chave v1 (Kernel↔Orbit, ADR-0002/G4)."""

from kernel.memory.session_key import memory_session_key, v1_memory_key


def test_v1_memory_key_without_session_id() -> None:
    assert v1_memory_key("discord", "u1", "chan1") == "discord:u1:chan1"


def test_v1_memory_key_with_session_id() -> None:
    assert v1_memory_key("discord", "u1", "chan1", "sess_abcd12") == "discord:u1:chan1:sess_abcd12"


def test_v1_memory_key_isolates_platforms_and_users() -> None:
    base = v1_memory_key("discord", "u1", "chan1", "sess_abcd12")
    other_platform = v1_memory_key("telegram", "u1", "chan1", "sess_abcd12")
    other_user = v1_memory_key("discord", "u2", "chan1", "sess_abcd12")
    assert base != other_platform
    assert base != other_user
    assert other_platform != other_user


def test_memory_session_key_legacy_still_works() -> None:
    assert memory_session_key("discord", "u1", "sess_abcd12") == "discord:u1:sess_abcd12"
    assert memory_session_key("cli", "u1", None) is None


def test_v1_memory_key_rejects_delimiter_injection_collision() -> None:
    """SEC-001 (gate S1): ``channel_id``/``platform``/``user_id`` sem allowlist de
    caracteres não podem colidir com uma tupla diferente via ':' embutido —
    caso contrário um chamador autenticado no canal lê/limpa o transcript de
    outra identidade (quebra de G4/isolamento por chave)."""
    vitima = v1_memory_key("a", "b", "c", "abcdef12")
    atacante = v1_memory_key("a", "b", "c:abcdef12", None)
    assert vitima != atacante
