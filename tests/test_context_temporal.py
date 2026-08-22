"""Testes do contexto temporal (data/hora oficiais do servidor)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from kernel.context.temporal import (
    TemporalContextProvider,
    format_date_pt,
    weekday_name_pt,
)

# 2026-08-08 é um sábado; 23:30 UTC = 20:30 em America/Sao_Paulo (UTC-3).
_FIXED_UTC = datetime(2026, 8, 8, 23, 30, 0, tzinfo=timezone.utc)


def _provider(tz: str = "America/Sao_Paulo") -> TemporalContextProvider:
    return TemporalContextProvider(tz, clock=lambda: _FIXED_UTC)


def test_now_converts_to_configured_timezone():
    ctx = _provider().now()
    assert ctx.date_iso == "2026-08-08"
    assert ctx.time_hm == "20:30"
    assert ctx.timezone_name == "America/Sao_Paulo"
    assert ctx.timestamp_iso.endswith("-03:00")


def test_weekday_and_date_in_portuguese():
    ctx = _provider().now()
    assert ctx.weekday_name == "sábado"
    assert format_date_pt(ctx.today) == "sábado, 8 de agosto de 2026"


def test_other_timezone_changes_local_date():
    # 23:30 UTC de sábado ainda é sábado em UTC, mas já é domingo em Tóquio.
    ctx = _provider("Asia/Tokyo").now()
    assert ctx.date_iso == "2026-08-09"
    assert ctx.weekday_name == "domingo"


def test_naive_clock_is_treated_as_utc():
    provider = TemporalContextProvider(
        "America/Sao_Paulo", clock=lambda: datetime(2026, 8, 8, 23, 30, 0)
    )
    assert provider.now().time_hm == "20:30"


def test_prompt_block_contains_official_data_and_priority_note():
    block = _provider().now().prompt_block()
    assert "Contexto temporal" in block
    assert "2026-08-08" in block
    assert "20:30" in block
    assert "America/Sao_Paulo" in block
    assert "fonte oficial" in block


def test_to_trace_data_has_no_secrets_and_full_temporal_fields():
    data = _provider().now().to_trace_data()
    assert set(data) == {"date", "time", "weekday", "timezone", "timestamp"}
    assert data["weekday"] == "sábado"


def test_invalid_timezone_raises():
    with pytest.raises(Exception):
        TemporalContextProvider("Not/AZone")


def test_settings_load_rejects_invalid_kernel_timezone(monkeypatch, tmp_path):
    from kernel.config import Settings

    monkeypatch.setenv("ACL_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("KERNEL_TIMEZONE", "Marte/CrateraGale")
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    with pytest.raises(RuntimeError, match="KERNEL_TIMEZONE"):
        Settings.load()


def test_settings_load_defaults_to_sao_paulo(monkeypatch):
    from kernel.config import Settings

    monkeypatch.setenv("ACL_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("KERNEL_TIMEZONE", raising=False)
    monkeypatch.delenv("KERNELBOT_ENV", raising=False)
    settings = Settings.load()
    assert settings.kernel_timezone == "America/Sao_Paulo"
    assert settings.context_dir is not None
    assert settings.calendar_path is not None
    assert settings.identity_prompt  # identity.txt embarcado no repo
