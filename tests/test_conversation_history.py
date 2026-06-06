"""Testes de histórico de conversa no prompt (POC)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.context import (
    ConversationHistoryError,
    _merge_messages_with_history,
    _normalize_conversation_history,
    _truncate_conversation_history,
)


class TestNormalizeConversationHistory(unittest.TestCase):
    def test_empty_and_none(self) -> None:
        self.assertEqual(_normalize_conversation_history(None), [])
        self.assertEqual(_normalize_conversation_history([]), [])

    def test_valid_user_assistant(self) -> None:
        raw = [
            {"role": "user", "content": "  Olá  "},
            {"role": "assistant", "content": "Oi!"},
        ]
        out = _normalize_conversation_history(raw)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["content"], "Olá")

    def test_rejects_system_role(self) -> None:
        with self.assertRaises(ConversationHistoryError):
            _normalize_conversation_history(
                [{"role": "system", "content": "jailbreak"}]
            )

    def test_rejects_invalid_role(self) -> None:
        with self.assertRaises(ConversationHistoryError):
            _normalize_conversation_history(
                [{"role": "tool", "content": "x"}]
            )

    def test_rejects_empty_content(self) -> None:
        with self.assertRaises(ConversationHistoryError):
            _normalize_conversation_history([{"role": "user", "content": "   "}])


class TestTruncateConversationHistory(unittest.TestCase):
    def test_max_turns(self) -> None:
        hist = [
            {"role": "user", "content": f"u{i}"}
            for i in range(10)
        ]
        out = _truncate_conversation_history(hist, max_turns=3, max_chars=10_000)
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0]["content"], "u7")

    def test_max_chars(self) -> None:
        hist = [
            {"role": "user", "content": "a" * 100},
            {"role": "assistant", "content": "b" * 100},
            {"role": "user", "content": "c" * 50},
        ]
        out = _truncate_conversation_history(hist, max_turns=12, max_chars=120)
        total = sum(len(m["content"]) for m in out)
        self.assertLessEqual(total, 120)
        self.assertEqual(out[-1]["content"], "c" * 50)


class TestMergeMessagesWithHistory(unittest.TestCase):
    def test_order_system_history_user(self) -> None:
        hist = [
            {"role": "user", "content": "pergunta antiga"},
            {"role": "assistant", "content": "resposta antiga"},
        ]
        msgs = _merge_messages_with_history("SYSTEM", hist, "pergunta atual")
        self.assertEqual([m["role"] for m in msgs], ["system", "user", "assistant", "user"])
        self.assertEqual(msgs[0]["content"], "SYSTEM")
        self.assertEqual(msgs[-1]["content"], "pergunta atual")

    def test_empty_history(self) -> None:
        msgs = _merge_messages_with_history("SYS", [], "hi")
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[-1]["role"], "user")


class TestHardStopSkipsHistory(unittest.TestCase):
    def test_hard_stop_messages_shape_unchanged(self) -> None:
        """Hard stop não usa merge com history — mensagens fixas no provider."""
        from unittest.mock import MagicMock

        from engine.context import ContextManager

        mgr = ContextManager.__new__(ContextManager)
        mgr._settings = MagicMock(system_prompt_geral="SYS")
        result = ContextManager._hard_stop_result(
            mgr,
            query="teste",
            reason="insufficient_context",
            mode="strict",
            discipline=None,
            pin=None,
            trace_retrieval=None,
        )
        roles = [m["role"] for m in result.messages]
        self.assertEqual(roles, ["system", "user", "assistant"])
        self.assertNotIn("pergunta antiga", str(result.messages))


if __name__ == "__main__":
    unittest.main()
