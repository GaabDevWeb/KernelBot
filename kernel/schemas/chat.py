"""Contratos HTTP do endpoint de conversa."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kernel.schemas.channel import ChannelContext
from kernel.schemas.validators import strip_and_require, validate_metadata, validate_session_id

Confidence = Literal["low", "medium", "high"]
_CONFIDENCE_VALUES: dict[Confidence, float] = {"low": 0.4, "medium": 0.7, "high": 0.95}


def confidence_to_float(value: str | None) -> float:
    return _CONFIDENCE_VALUES.get(value if value in _CONFIDENCE_VALUES else "low", 0.4)


class HistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8192)

    @field_validator("content", mode="after")
    @classmethod
    def sanitize_history_content(cls, value: str) -> str:
        # Neutraliza bytes nulos e reduz spoofing grosseiro de system role
        cleaned = value.replace("\x00", "").strip()
        if not cleaned:
            raise ValueError("content não pode ser vazio")
        return cleaned


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=16000)
    user_id: str | None = Field(default=None, max_length=256)
    channel: str = Field(default="unknown", min_length=1, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)
    discipline: str | None = Field(default=None, max_length=128)
    session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{8,128}$")
    history: list[HistoryItem] = Field(default_factory=list, max_length=40)
    stream: bool = False

    @field_validator("message", "discipline", "user_id", "channel", mode="after")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        return strip_and_require(value)

    @field_validator("metadata", mode="after")
    @classmethod
    def bound_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata(value)

    @field_validator("session_id", mode="after")
    @classmethod
    def opaque_session(cls, value: str | None) -> str | None:
        return validate_session_id(value)


class ChatRequestV1(BaseModel):
    """Contrato v1 multi-canal (Kernel↔Orbit, ADR-0002): identidade em ``context``."""

    model_config = ConfigDict(extra="forbid")
    context: ChannelContext
    message: str = Field(min_length=1, max_length=16000)
    discipline: str | None = Field(default=None, max_length=128)
    history: list[HistoryItem] = Field(default_factory=list, max_length=40)
    metadata: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False
    reset_context: bool = False

    @field_validator("message", "discipline", mode="after")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        return strip_and_require(value)

    @field_validator("metadata", mode="after")
    @classmethod
    def bound_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata(value)


class ChatResponse(BaseModel):
    answer: str
    discipline: str | None
    sources: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any]
