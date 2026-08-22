"""Conversão do stream SSE interno no contrato JSON canónico."""
from __future__ import annotations
import json
from collections.abc import AsyncIterator
from typing import Any

async def aggregate_sse(stream: AsyncIterator[str]) -> tuple[str, dict[str, Any]]:
    text: list[str] = []
    metadata: dict[str, Any] = {}
    async for event in stream:
        for line in event.splitlines():
            if not line.startswith("data: "):
                continue
            value = line[6:]
            if value == "[DONE]":
                continue
            if value.startswith("[ACL_META]"):
                try:
                    metadata.update(json.loads(value.removeprefix("[ACL_META]")))
                except json.JSONDecodeError:
                    continue
                continue
            text.append(value.replace("\\n", "\n"))
    return "".join(text), metadata
