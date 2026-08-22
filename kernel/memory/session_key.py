"""Chave de memória/pin isolada por canal e utilizador."""

from __future__ import annotations

from urllib.parse import quote

_KEY_SAFE_CHARS = ""  # força escaping de ":" e "/" (nenhum caractere extra é seguro)


def memory_session_key(
    channel: str | None,
    user_id: str | None,
    session_id: str | None,
) -> str | None:
    """Compõe chave opaca de pin: ``channel:user_id:session_id``.

    Impede que dois canais/utilizadores partilhem pin só porque reutilizam
    o mesmo ``session_id`` (ex.: ``user_id`` numérico como sessão).
    """
    if not session_id:
        return None
    ch = (channel or "unknown").strip() or "unknown"
    uid = (user_id or "_anon").strip() or "_anon"
    return f"{ch}:{uid}:{session_id}"


def v1_memory_key(
    platform: str,
    user_id: str,
    channel_id: str,
    session_id: str | None = None,
) -> str:
    """Compõe a chave v1 (Kernel↔Orbit, ADR-0002/G4): ``platform:user_id:channel_id[:session_id]``.

    Ao contrário de :func:`memory_session_key` (que devolve ``None`` sem
    ``session_id``), esta função **nunca** devolve ``None`` — é a chave
    primária de isolamento de ``TranscriptStore``/``PinnedSessionStore`` por
    canal em `/v1/chat`, com ou sem sessão explícita do cliente.

    Cada segmento é percent-encoded (``:`` e ``/`` incluídos) antes de ser
    juntado com ``:`` — ``platform``/``user_id``/``channel_id`` não têm
    allowlist de caracteres (só tamanho/non-empty), logo um ``channel_id``
    contendo ``":"`` poderia, sem este escaping, produzir a mesma chave que
    outra tupla (ex.: ``channel_id="c:abcdef12"`` sem sessão colidia com
    ``channel_id="c"`` + ``session_id="abcdef12"``), quebrando o isolamento
    exigido por G4 (achado SEC-001 do gate S1).
    """
    segments = [platform, user_id, channel_id]
    if session_id:
        segments.append(session_id)
    return ":".join(quote(segment, safe=_KEY_SAFE_CHARS) for segment in segments)
