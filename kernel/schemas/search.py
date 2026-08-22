"""Contratos HTTP do endpoint de retrieval."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kernel.schemas.validators import strip_and_require, validate_metadata, validate_session_id


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=16000)
    user_id: str | None = Field(default=None, max_length=256)
    channel: str = Field(default="unknown", min_length=1, max_length=64)
    discipline: str | None = Field(default=None, max_length=128)
    session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{8,128}$")
    metadata: dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=5, ge=1, le=20)

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


class SearchCandidate(BaseModel):
    source: str
    score: float
    score_normalized: float
    snippet: str


class SearchResponse(BaseModel):
    discipline: str | None
    decision: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[str]
    candidates: list[SearchCandidate]
    metadata: dict[str, Any]
