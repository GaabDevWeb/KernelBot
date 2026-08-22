"""Contrato de identidade multi-canal (Kernel↔Orbit — ADR-0002, RF-001)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kernel.schemas.validators import strip_and_require, validate_session_id


class ChannelContext(BaseModel):
    """Identidade opaca do remetente, agnóstica de vendor (sem `jid`/`guild_id`/`phone`)."""

    model_config = ConfigDict(extra="forbid")
    platform: str = Field(min_length=1, max_length=64)
    user_id: str = Field(min_length=1, max_length=256)
    channel_id: str = Field(min_length=1, max_length=256)
    session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{8,128}$")

    @field_validator("platform", "user_id", "channel_id", mode="after")
    @classmethod
    def strip_strings(cls, value: str) -> str:
        cleaned = strip_and_require(value)
        if cleaned is None:
            raise ValueError("campo não pode ser vazio")
        return cleaned

    @field_validator("session_id", mode="after")
    @classmethod
    def opaque_session(cls, value: str | None) -> str | None:
        return validate_session_id(value)
