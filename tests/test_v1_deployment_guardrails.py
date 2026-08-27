"""Guardrails de deploy V1 — fail-fast para combinações perigosas."""

from __future__ import annotations

import pytest

from api.security import require_api_auth, validate_deployment_guardrails, validate_production_security_config


def test_staging_requires_api_auth_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KERNELBOT_ENV", "staging")
    monkeypatch.delenv("ACL_REQUIRE_API_AUTH", raising=False)
    assert require_api_auth() is True


def test_production_rejects_multi_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KERNELBOT_ENV", "production")
    monkeypatch.setenv("KERNEL_WORKERS", "4")
    with pytest.raises(RuntimeError, match="workers"):
        validate_deployment_guardrails()


def test_production_single_worker_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KERNELBOT_ENV", "production")
    monkeypatch.setenv("KERNEL_WORKERS", "1")
    validate_deployment_guardrails()


def test_production_fail_fast_still_requires_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KERNELBOT_ENV", "production")
    monkeypatch.setenv("KERNEL_WORKERS", "1")
    monkeypatch.delenv("ACL_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("ACL_CHANNEL_API_KEYS", raising=False)
    monkeypatch.delenv("ACL_INTERNAL_BEARER_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="ACL_"):
        validate_production_security_config()
