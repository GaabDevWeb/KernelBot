"""Replay + Diff do Flight Recorder."""

from __future__ import annotations

import difflib
from typing import Any


def text_diff(original: str, replayed: str) -> dict[str, Any]:
    a = (original or "").splitlines()
    b = (replayed or "").splitlines()
    unified = list(
        difflib.unified_diff(a, b, fromfile="original", tofile="replay", lineterm="")
    )
    ratio = difflib.SequenceMatcher(None, original or "", replayed or "").ratio()
    return {
        "identical": (original or "") == (replayed or ""),
        "similarity": round(ratio, 4),
        "unified": "\n".join(unified),
        "original_chars": len(original or ""),
        "replay_chars": len(replayed or ""),
    }


def extract_replay_inputs(snapshot: dict[str, Any] | None, events: list[Any]) -> dict[str, Any]:
    """Extrai message + transcript para reexecução."""
    conv = (snapshot or {}).get("conversation") or {}
    message = conv.get("message")
    transcript = ((snapshot or {}).get("prompt") or {}).get("transcript") or []
    if not message:
        for e in events:
            data = getattr(e, "data", None) or {}
            if getattr(e, "stage", "") in {"REQUEST_RECEIVED", "MESSAGE_RECEIVED", "MESSAGE_PARSED"}:
                message = data.get("message_preview") or data.get("message") or message
    return {
        "message": message or "",
        "transcript": transcript if isinstance(transcript, list) else [],
        "user": conv.get("user"),
        "channel": conv.get("channel"),
        "answer_original": conv.get("answer"),
    }
