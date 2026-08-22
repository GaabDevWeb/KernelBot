"""Validação de anexos — allowlist de tipo/extensão/tamanho."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

# Extensões permitidas (Fase 8 + segurança Fase 12)
ALLOWED_EXT = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".pdf",
    ".docx",
    ".mp4",
    ".mp3",
    ".zip",
    ".ogg",
    ".webm",
}

EXT_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".mp4": "video/mp4",
    ".mp3": "audio/mpeg",
    ".zip": "application/zip",
    ".ogg": "audio/ogg",
    ".webm": "video/webm",
}

# Bloquear executáveis / scripts mesmo se alguém renomear
BLOCKED_EXT = {
    ".exe",
    ".bat",
    ".cmd",
    ".sh",
    ".ps1",
    ".js",
    ".mjs",
    ".html",
    ".htm",
    ".svg",
    ".php",
    ".py",
    ".dll",
    ".so",
    ".msi",
    ".scr",
}

MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024  # 8 MiB
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._\- ]+")


class AttachmentRejected(ValueError):
    pass


def sanitize_filename(name: str) -> str:
    base = Path(name or "file").name
    cleaned = SAFE_NAME_RE.sub("_", base).strip(" ._") or "file"
    return cleaned[:160]


def validate_upload(*, filename: str, size: int, content_type: str | None = None) -> tuple[str, str]:
    if size <= 0:
        raise AttachmentRejected("Ficheiro vazio.")
    if size > MAX_ATTACHMENT_BYTES:
        raise AttachmentRejected(f"Ficheiro excede {MAX_ATTACHMENT_BYTES // (1024*1024)} MiB.")
    safe = sanitize_filename(filename)
    ext = Path(safe).suffix.lower()
    if ext in BLOCKED_EXT:
        raise AttachmentRejected(f"Extensão bloqueada: {ext}")
    if ext not in ALLOWED_EXT:
        raise AttachmentRejected(f"Extensão não permitida: {ext or '(sem)'}")
    mime = EXT_MIME.get(ext, (content_type or "application/octet-stream").split(";")[0].strip())
    # rejeitar content-types perigosos
    ct = (content_type or "").lower()
    if "javascript" in ct or "html" in ct or ct in {"text/html", "application/xhtml+xml"}:
        raise AttachmentRejected("Content-Type não permitido.")
    return safe, mime


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_template(body: str, variables: dict[str, str] | None = None) -> str:
    """Substitui {var} — sem avaliação HTML/JS."""
    text = body or ""
    # strip tags activas grosseiras
    text = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", text, flags=re.I | re.S)
    text = re.sub(r"on\w+\s*=", "", text, flags=re.I)
    vars_map = {str(k): str(v) for k, v in (variables or {}).items()}
    def _repl(m: re.Match[str]) -> str:
        key = m.group(1)
        return vars_map.get(key, m.group(0))
    return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", _repl, text)
