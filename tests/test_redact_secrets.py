from kernel.structured_log import redact_secrets


def test_redact_bearer_and_api_keys() -> None:
    text = "Authorization: Bearer abc.def-ghi OPENROUTER_API_KEY=sk-or-v1-secret123456"
    out = redact_secrets(text)
    assert "abc.def-ghi" not in out
    assert "sk-or-v1-secret123456" not in out
    assert "***" in out
