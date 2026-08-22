"""Contratos Pydantic para APIs de Grupos e Memória de Canal."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GroupMessageItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message_id: str = Field(min_length=1, max_length=256)
    user_id: str = Field(min_length=1, max_length=256)
    sender_name: str = Field(default="", max_length=256)
    timestamp: str | None = None
    content: str = Field(min_length=1, max_length=16000)
    reply_to: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GroupMessagesBatchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    platform: str = Field(default="whatsapp", min_length=1, max_length=64)
    channel_id: str = Field(min_length=1, max_length=256)
    messages: list[GroupMessageItem] = Field(default_factory=list, max_length=200)


class GroupStateUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    introduction_sent: bool
