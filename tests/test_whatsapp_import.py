"""Testes do parser WhatsApp — apenas fixtures sintéticas."""

from __future__ import annotations

from pathlib import Path

from kernel.memory.group_memory import GroupMemoryStore
from kernel.memory.whatsapp_import import (
    messages_to_store_payload,
    parse_whatsapp_export_file,
    parse_whatsapp_export_lines,
)


SYNTHETIC_EXPORT = """\
[15/03/2026, 10:00:00] Ana Silva: Quando é a prova de Python?
[15/03/2026, 10:01:12] Bruno Costa: Acho que é sexta, mas não tenho certeza
[15/03/2026, 10:02:00] Ana Silva: https://example.com/edital prova
[15/03/2026, 10:03:00] Carlos Lima: <Mídia oculta>
[15/03/2026, 10:04:00] Ana Silva: Mensagem apagada
[15/03/2026, 10:05:00] Bruno Costa: Trabalho sobre recursividade (editada)
15/03/2026, 10:06 - Ana Silva: Formato dash também funciona
Messages and calls are end-to-end encrypted. No one outside of this chat...
"""


def test_parse_synthetic_whatsapp_export() -> None:
    lines = SYNTHETIC_EXPORT.splitlines(keepends=True)
    parsed, stats = parse_whatsapp_export_lines(iter(lines), channel_id="group-test@g.us")
    assert stats.messages_parsed >= 5
    assert stats.skipped_system >= 1
    assert stats.media_only >= 1
    assert stats.deleted >= 1
    assert stats.edited >= 1
    assert stats.with_links >= 1
    ids = {m.message_id for m in parsed}
    assert len(ids) == len(parsed)


def test_import_idempotent(tmp_path: Path) -> None:
    export = tmp_path / "export.txt"
    export.write_text(SYNTHETIC_EXPORT, encoding="utf-8")
    db = tmp_path / "gm.sqlite3"
    store = GroupMemoryStore(db)

    parsed, _ = parse_whatsapp_export_file(export, channel_id="group-test@g.us")
    payload = messages_to_store_payload(parsed, platform="whatsapp", channel_id="group-test@g.us")

    n1 = store.record_messages_batch(payload)
    n2 = store.record_messages_batch(payload)
    assert n1 > 0
    assert n2 > 0
    assert store.count_messages("whatsapp", "group-test@g.us") == n1


def test_deleted_excluded_from_bm25(tmp_path: Path) -> None:
    store = GroupMemoryStore(tmp_path / "gm2.sqlite3")
    store.record_message(
        platform="whatsapp",
        channel_id="g1@g.us",
        message_id="active-1",
        user_id="u1",
        sender_name="Ana",
        content="Trabalho sobre recursividade na turma",
        timestamp="2026-08-20T10:00:00.000Z",
    )
    store.record_message(
        platform="whatsapp",
        channel_id="g1@g.us",
        message_id="del-1",
        user_id="u2",
        sender_name="Bob",
        content="[mensagem apagada]",
        timestamp="2026-08-21T10:00:00.000Z",
        metadata={"message_status": "deleted", "message_type": "deleted"},
    )
    hits = store.search_historical("whatsapp", "g1@g.us", "recursividade")
    assert len(hits) == 1
    assert hits[0].message_id == "active-1"


def test_context_router_group_memory_signal() -> None:
    from kernel.context.router import ContextRouter
    from kernel.context.types import RouteSignals

    router = ContextRouter()
    route = router.route(
        "O que a turma decidiu sobre o trabalho?",
        signals=RouteSignals(history_turns=0),
    )
    assert route.use_group_memory is True

    route2 = router.route(
        "Que horas são?",
        signals=RouteSignals(history_turns=0),
    )
    assert route2.use_group_memory is False
