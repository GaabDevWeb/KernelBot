"""Parser de export WhatsApp (.txt) → mensagens estruturadas (sem I/O de DB).

Suporta formatos comuns (iOS/Android/desktop). Não altera o ficheiro fonte.
Conteúdo real nunca deve ir para testes — usar fixtures sintéticas.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

# [DD/MM/YYYY, HH:MM:SS] Author: message  |  DD/MM/YYYY, HH:MM - Author: message
_LINE_BRACKET = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APMapm]{2})?)\]\s"
    r"([^:]+?):\s(.*)$"
)
_LINE_DASH = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APMapm]{2})?)\s+-\s+"
    r"([^:]+?):\s(.*)$"
)
# DD/MM/YYYY HH:MM - evento sistema (sem autor:)
_LINE_DASH_SYSTEM = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APMapm]{2})?)\s+-\s+(.*)$"
)

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

_DELETED_MARKERS = (
    "this message was deleted",
    "mensagem apagada",
    "you deleted this message",
    "você apagou esta mensagem",
    "eliminaste esta mensagem",
)
_EDITED_SUFFIXES = (" (edited)", " (editada)", " (editado)")
_MEDIA_MARKERS = (
    "<mídia oculta>",
    "<media omitted>",
    "image omitted",
    "video omitted",
    "audio omitted",
    "document omitted",
    "sticker omitted",
    "gif omitted",
    "ptt omitted",
    "arquivo anexado",
    "attached:",
)

_SYSTEM_PREFIXES = (
    "messages and calls are end-to-end encrypted",
    "as mensagens e chamadas são protegidas",
    "you created group",
    "você criou o grupo",
    "changed the subject",
    "alterou o assunto",
    "added you",
    "adicionou você",
    "left",
    "saiu",
    "joined using",
)


@dataclass
class ParsedWhatsAppMessage:
    message_id: str
    user_id: str
    sender_name: str
    timestamp: str
    content: str
    reply_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    line_no: int = 0


@dataclass
class WhatsAppImportStats:
    lines_read: int = 0
    messages_parsed: int = 0
    skipped_system: int = 0
    skipped_empty: int = 0
    media_only: int = 0
    deleted: int = 0
    edited: int = 0
    with_links: int = 0
    parse_errors: int = 0


def _parse_date(date_part: str, time_part: str) -> datetime | None:
    time_part = time_part.strip().upper()
    for fmt in (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%y %H:%M:%S",
        "%d/%m/%y %H:%M",
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%y %I:%M:%S %p",
        "%d/%m/%y %I:%M %p",
    ):
        try:
            dt = datetime.strptime(f"{date_part} {time_part}", fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _iso_ts(dt: datetime | None, fallback: str = "") -> str:
    if dt is None:
        return fallback or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _stable_message_id(timestamp: str, sender: str, content: str, line_no: int) -> str:
    raw = f"{timestamp}|{sender}|{content[:200]}|{line_no}".encode("utf-8")
    return "wa_" + hashlib.sha256(raw).hexdigest()[:24]


def _extract_links(text: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for url in _URL_RE.findall(text):
        try:
            host = urlparse(url).netloc or ""
        except Exception:
            host = ""
        links.append({"url": url, "host": host})
    return links


def _classify_content(raw: str) -> tuple[str, dict[str, Any]]:
    """Normaliza conteúdo e metadados (editada/apagada/mídia/links)."""
    meta: dict[str, Any] = {"source": "whatsapp_export"}
    text = raw.strip()
    lower = text.lower()

    for marker in _DELETED_MARKERS:
        if marker in lower:
            meta["message_status"] = "deleted"
            meta["message_type"] = "deleted"
            return text or "[mensagem apagada]", meta

    for suffix in _EDITED_SUFFIXES:
        if lower.endswith(suffix):
            meta["message_status"] = "edited"
            meta["message_type"] = "text"
            text = text[: -len(suffix)].rstrip()
            break

    if any(m in lower for m in _MEDIA_MARKERS):
        meta["message_type"] = "media"
        if not text:
            text = "[mídia]"
        return text, meta

    links = _extract_links(text)
    if links:
        meta["links"] = links
        meta["message_type"] = meta.get("message_type", "text")

    meta.setdefault("message_type", "text")
    meta.setdefault("message_status", "active")
    return text, meta


def _is_system_line(sender: str, content: str) -> bool:
    blob = f"{sender} {content}".lower()
    return any(blob.startswith(p) or p in blob for p in _SYSTEM_PREFIXES)


def _normalize_line(raw: str) -> str:
    # WhatsApp export (Android) inclui LTR marks invisíveis
    return raw.replace("\u200e", "").replace("\u200f", "").replace("\ufeff", "").strip()


def _match_header(line: str) -> tuple[str, str, str, str] | None:
    line = _normalize_line(line)
    m = _LINE_BRACKET.match(line) or _LINE_DASH.match(line)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3).strip(), m.group(4)


def parse_whatsapp_export_lines(
    lines: Iterator[str],
    *,
    channel_id: str = "",
) -> tuple[list[ParsedWhatsAppMessage], WhatsAppImportStats]:
    """Parse linha a linha (streaming). Não modifica o ficheiro original."""
    stats = WhatsAppImportStats()
    out: list[ParsedWhatsAppMessage] = []
    current: ParsedWhatsAppMessage | None = None

    for line_no, raw_line in enumerate(lines, start=1):
        stats.lines_read += 1
        line = _normalize_line(raw_line.rstrip("\n\r"))
        if not line.strip():
            continue

        lower_line = line.lower()
        sys_dash = _LINE_DASH_SYSTEM.match(line)
        if sys_dash:
            sys_body = sys_dash.group(3).strip()
            if _is_system_line("", sys_body) or any(
                p in lower_line
                for p in (
                    "entrou usando",
                    "foi adicionado",
                    "removeu",
                    "criou este grupo",
                    "saiu",
                    "alterou",
                )
            ):
                stats.skipped_system += 1
                current = None
                continue

        if not _match_header(line) and any(lower_line.startswith(p) for p in _SYSTEM_PREFIXES):
            stats.skipped_system += 1
            continue

        header = _match_header(line)
        if header:
            if current is not None:
                out.append(current)
            date_part, time_part, sender, content = header
            dt = _parse_date(date_part, time_part)
            ts = _iso_ts(dt)
            if _is_system_line(sender, content):
                stats.skipped_system += 1
                current = None
                continue

            body, meta = _classify_content(content)
            if meta.get("message_status") == "deleted":
                stats.deleted += 1
            if meta.get("message_status") == "edited":
                stats.edited += 1
            if meta.get("message_type") == "media":
                stats.media_only += 1
            if meta.get("links"):
                stats.with_links += 1

            if not body.strip() and meta.get("message_type") != "media":
                stats.skipped_empty += 1
                current = None
                continue

            user_id = hashlib.sha256(sender.encode("utf-8")).hexdigest()[:16]
            mid = _stable_message_id(ts, sender, body, line_no)
            if channel_id:
                meta["channel_id"] = channel_id

            current = ParsedWhatsAppMessage(
                message_id=mid,
                user_id=user_id,
                sender_name=sender,
                timestamp=ts,
                content=body,
                metadata=meta,
                line_no=line_no,
            )
            stats.messages_parsed += 1
            continue

        # continuação multilinha
        if current is not None:
            current.content = f"{current.content}\n{line}".strip()
            body, extra = _classify_content(current.content)
            current.content = body
            current.metadata.update(extra)
        else:
            stats.parse_errors += 1

    if current is not None:
        out.append(current)

    return out, stats


def parse_whatsapp_export_file(
    path: Path | str,
    *,
    channel_id: str = "",
    encoding: str = "utf-8",
) -> tuple[list[ParsedWhatsAppMessage], WhatsAppImportStats]:
    """Lê ficheiro .txt exportado do WhatsApp (read-only)."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Export não encontrado: {p}")
    with p.open("r", encoding=encoding, errors="replace") as fh:
        return parse_whatsapp_export_lines(fh, channel_id=channel_id)


def messages_to_store_payload(
    parsed: list[ParsedWhatsAppMessage],
    *,
    platform: str,
    channel_id: str,
) -> list[dict[str, Any]]:
    return [
        {
            "platform": platform,
            "channel_id": channel_id,
            "message_id": m.message_id,
            "user_id": m.user_id,
            "sender_name": m.sender_name,
            "timestamp": m.timestamp,
            "content": m.content,
            "reply_to": m.reply_to,
            "metadata": m.metadata,
        }
        for m in parsed
    ]
