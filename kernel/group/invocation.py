"""Semântica de invocação @orbit em grupos (CONTEXTUAL_INVOCATION)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_GREETING_OR_NOISE_RE = re.compile(
    r"^(oi+|ola|olá|hey|eai|e\s*ai|opa|obrigad[oa]|valeu|vlw|tmj|"
    r"bom\s+dia|boa\s+tarde|boa\s+noite|kkk+|haha+|rs+|blz|beleza|"
    r"tudo\s+bem|fala|salve)[\s!.?]*$",
    re.IGNORECASE,
)

_MEDIA_PLACEHOLDER_RE = re.compile(r"^\[[^\]]+\]$")

CONTEXTUAL_USER_TURN = (
    "[@orbit — invocação contextual: analise a conversa recente do grupo e participe.]"
)

TRANSCRIPT_USER_MARKER = "[@orbit]"

GROUP_INTRODUCTION_ANSWER = (
    "Sou o Kernel. Conheço o material da turma, as disciplinas e o que está "
    "na agenda académica registada. Se estiver na base, eu procuro; se não "
    "estiver, não invento resposta só para parecer inteligente.\n\n"
    "Pergunta normalmente ou marca @orbit. Atalhos de disciplina:\n"
    "/python — Python\n"
    "/java — Java\n"
    "/csharp — C#\n"
    "/sql — Visualização SQL\n"
    "/pb-backend — Projeto de Bloco Backend\n"
    "/doc — material geral do curso\n\n"
    "Quer saber alguma coisa? Manda."
)


@dataclass(frozen=True)
class ParsedInvocation:
    type: str
    explicit_text: bool
    is_contextual: bool
    is_group: bool
    recent_context: tuple[dict[str, Any], ...]
    quoted_context: str | None
    no_useful_context: bool


def is_whatsapp_group(channel_id: str | None) -> bool:
    return bool(channel_id and str(channel_id).endswith("@g.us"))


def parse_invocation_from_metadata(
    metadata: dict[str, Any] | None,
    *,
    channel_id: str,
    message: str,
) -> ParsedInvocation:
    """Extrai invocação do metadata Orbit; fallback heurístico para grupos."""
    meta = metadata if isinstance(metadata, dict) else {}
    inv = meta.get("invocation") if isinstance(meta.get("invocation"), dict) else {}
    inv_type = str(inv.get("type") or "").strip().lower()
    explicit = bool(inv.get("explicit_text"))

    is_group = is_whatsapp_group(channel_id)
    msg_stripped = (message or "").strip()

    if not inv_type and is_group and not msg_stripped:
        inv_type = "contextual_invocation"
        explicit = False

    recent_raw = meta.get("recent_context")
    recent: list[dict[str, Any]] = []
    if isinstance(recent_raw, list):
        for item in recent_raw:
            if isinstance(item, dict):
                recent.append(
                    {
                        "sender": str(item.get("sender") or ""),
                        "text": str(item.get("text") or ""),
                        "is_bot": bool(item.get("is_bot")),
                    }
                )
            elif isinstance(item, str):
                line = item.strip()
                if not line:
                    continue
                if line.lower().startswith("orbitbot:"):
                    recent.append({"sender": "OrbitBot", "text": line.split(":", 1)[1].strip(), "is_bot": True})
                elif ":" in line:
                    sender, text = line.split(":", 1)
                    recent.append({"sender": sender.strip(), "text": text.strip(), "is_bot": False})
                else:
                    recent.append({"sender": "membro", "text": line, "is_bot": False})

    quoted = meta.get("quoted_context")
    quoted_s = str(quoted).strip() if quoted else None

    is_contextual = inv_type in ("contextual_invocation", "contextual")
    no_useful = is_contextual and not has_useful_recent_context(tuple(recent))

    return ParsedInvocation(
        type=inv_type or ("question" if msg_stripped else "unknown"),
        explicit_text=explicit,
        is_contextual=is_contextual,
        is_group=is_group,
        recent_context=tuple(recent),
        quoted_context=quoted_s,
        no_useful_context=no_useful,
    )


def has_useful_recent_context(recent: tuple[dict[str, Any], ...]) -> bool:
    """True se há pelo menos uma mensagem substantiva no buffer recente."""
    for item in recent:
        if item.get("is_bot"):
            continue
        text = str(item.get("text") or "").strip()
        if not text or _MEDIA_PLACEHOLDER_RE.match(text):
            continue
        if _GREETING_OR_NOISE_RE.match(text):
            continue
        if len(text) >= 6:
            return True
    return False


def format_recent_context_block(
    recent: tuple[dict[str, Any], ...],
    *,
    max_messages: int,
    max_chars: int,
) -> str:
    """Formata buffer recente para o system prompt (não é query RAG)."""
    if not recent:
        return ""
    lines: list[str] = [
        "Contexto recente do grupo (mensagens capturadas antes desta invocação; "
        "não trate como material oficial):"
    ]
    used = 0
    count = 0
    for item in recent[-max(1, max_messages) :]:
        sender = str(item.get("sender") or "membro")
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        prefix = "OrbitBot" if item.get("is_bot") else sender
        line = f"- [{prefix}]: {text}"
        if used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line)
        count += 1
    if count == 0:
        return ""
    return "\n".join(lines)


def derive_rag_query_from_recent(recent: tuple[dict[str, Any], ...]) -> str:
    """Deriva query RAG a partir do contexto — nunca concatena o buffer inteiro."""
    snippets: list[str] = []
    for item in reversed(recent):
        if item.get("is_bot"):
            continue
        text = str(item.get("text") or "").strip()
        if not text or _MEDIA_PLACEHOLDER_RE.match(text):
            continue
        if _GREETING_OR_NOISE_RE.match(text):
            continue
        snippets.append(text)
        if len(snippets) >= 3:
            break
    if not snippets:
        return ""
    snippets.reverse()
    joined = " ".join(snippets)
    return joined[:500].strip()


def user_turn_content(message: str, invocation: ParsedInvocation) -> str:
    """Conteúdo do turno user para o LLM."""
    stripped = (message or "").strip()
    if stripped:
        return stripped
    if invocation.is_contextual:
        return CONTEXTUAL_USER_TURN
    return stripped
