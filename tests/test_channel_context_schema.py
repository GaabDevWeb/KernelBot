"""Testes de contrato v1 multi-canal (ChannelContext/ChatRequestV1 — ADR-0002)."""

import pytest
from pydantic import ValidationError

from kernel.schemas.chat import ChatRequestV1
from kernel.schemas.channel import ChannelContext

_VALID_CONTEXT = {"platform": "discord", "user_id": "u1", "channel_id": "chan1"}


def test_channel_context_rejects_vendor_field() -> None:
    with pytest.raises(ValidationError):
        ChannelContext(**_VALID_CONTEXT, jid="5511999999999@s.whatsapp.net")


def test_chat_request_v1_rejects_vendor_field_in_context() -> None:
    with pytest.raises(ValidationError):
        ChatRequestV1(
            context={**_VALID_CONTEXT, "jid": "5511999999999@s.whatsapp.net"},
            message="olá",
        )


def test_channel_context_rejects_digits_only_session_id() -> None:
    with pytest.raises(ValidationError):
        ChannelContext(**_VALID_CONTEXT, session_id="12345678")


def test_channel_context_accepts_none_session_id() -> None:
    context = ChannelContext(**_VALID_CONTEXT, session_id=None)
    assert context.session_id is None


def test_channel_context_accepts_minimal_valid_payload() -> None:
    context = ChannelContext(**_VALID_CONTEXT)
    assert context.platform == "discord"
    assert context.user_id == "u1"
    assert context.channel_id == "chan1"
    assert context.session_id is None


def test_chat_request_v1_accepts_minimal_valid_payload() -> None:
    request = ChatRequestV1(context=_VALID_CONTEXT, message="olá")
    assert request.context.platform == "discord"
    assert request.message == "olá"


def test_chat_request_v1_reset_context_defaults_false() -> None:
    request = ChatRequestV1(context=_VALID_CONTEXT, message="olá")
    assert request.reset_context is False
