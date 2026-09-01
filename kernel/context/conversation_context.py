"""Resolução conservadora de contexto conversacional (P0 V1 gate).

Sem LLM: dêiticos, ambiguidade curta, topic shift, conflitos sociais, mídia.
Fixtures sintéticas apenas nos testes — nunca corpus privado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_MEDIA_PLACEHOLDER_RE = re.compile(r"^\[[^\]]+\]$")

# Perguntas curtas / dêiticos — precisam de contexto recente para RAG.
_DEICTIC_OR_AMBIGUOUS_RE = re.compile(
    r"^(?:"
    r"isso|isto|aquilo|esse|essa|este|esta|aquele|aquela|"
    r"o\s+tp|a\s+tp|o\s+at|a\s+at|"
    r"qual\??|onde\??|quando\??|como\??|"
    r"como\s+faz\??|"
    r"manda|funcionou\??|deu\s+certo\??|"
    r"esse\??|essa\??|"
    r"e\s+(?:como|o\s+que|qual|isso|esse|essa)\??"
    r")[\s!.?]*$",
    re.IGNORECASE,
)

_GREETING_OR_NOISE_RE = re.compile(
    r"^(oi+|ola|olá|hey|eai|obrigad[oa]|valeu|vlw|"
    r"bom\s+dia|boa\s+tarde|boa\s+noite|kkk+|haha+|blz|beleza)[\s!.?]*$",
    re.IGNORECASE,
)

# Marcadores de tópico para evitar topic leakage (prioridade = ordem de scan).
_TOPIC_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("java", ("java", "switch", "oop", "classe", "método", "metodo", "jvm")),
    ("csharp", ("c#", "csharp", "dotnet", ".net", "switch", "foreach")),
    ("python", ("python", "pip", "pandas", "flask", "jupyter", "def ")),
    ("sql", ("sql", "select", "join", "banco", "tabela", "mysql", "sqlite")),
    ("backend", ("requisito", "caso de uso", "uml", "backend", "api rest")),
    ("ia", ("prompt", "llm", "token", "embedding", "ia generativa")),
)

_ACADEMIC_SHORTHAND: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\btp\b", re.I), "trabalho prático TP"),
    (re.compile(r"\bat\b", re.I), "atividade AT avaliação"),
    (re.compile(r"\bprova\b", re.I), "prova avaliação"),
    (re.compile(r"\btrabalho\b", re.I), "trabalho avaliação"),
)

# Conflitos sociais sobre datas académicas (não substituem calendário oficial).
_ACADEMIC_EVENT_RE = re.compile(r"\b(prova|at|tp|entrega|avaliação|avaliacao)\b", re.IGNORECASE)
_DAY_RE = re.compile(
    r"\b(segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)(?:-feira)?\b",
    re.IGNORECASE,
)


def _normalize_day(raw: str) -> str:
    d = raw.lower().replace("terca", "terça").replace("sabado", "sábado")
    if d == "segunda":
        return "segunda-feira"
    if not d.endswith("-feira") and d in {"terça", "quarta", "quinta", "sexta", "sábado"}:
        return f"{d}-feira"
    return d

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


@dataclass(frozen=True)
class ResolvedConversationQuery:
    """Resultado da resolução query + flags para trace."""

    original: str
    resolved: str
    was_resolved: bool
    resolution_k: int
    dominant_topic: str | None
    ambiguous_unresolved: bool
    reason: str | None = None


@dataclass(frozen=True)
class SocialConflictHint:
    """Conflito detectado no buffer recente (memória social)."""

    topic: str
    variants: tuple[str, ...]
    prompt_note: str


def is_media_placeholder(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if _MEDIA_PLACEHOLDER_RE.match(t):
        return True
    low = t.lower()
    return low in (
        "[mídia]",
        "[media omitted]",
        "<media omitted>",
        "image omitted",
        "video omitted",
        "audio omitted",
        "sticker omitted",
    ) or "media omitted" in low or "omitted" in low and t.startswith("<")


def is_deictic_or_ambiguous_query(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if len(t) > 80:
        return False
    if _DEICTIC_OR_AMBIGUOUS_RE.match(t):
        return True
    low = t.lower()
    if len(t) <= 48 and any(
        w in low for w in ("isso", "isto", "esse", "essa", "aquilo", "aquele", "aquela")
    ):
        return True
    alnum = re.sub(r"\W+", "", t)
    if len(alnum) <= 4 and "?" in t:
        return True
    return False


def _is_substantive(text: str) -> bool:
    t = (text or "").strip()
    if not t or is_media_placeholder(t):
        return False
    if _GREETING_OR_NOISE_RE.match(t):
        return False
    if len(t) < 4:
        return False
    return True


def select_recent_window(
    recent: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    *,
    k: int = 4,
) -> tuple[dict[str, Any], ...]:
    """Últimas K mensagens substantivas (não bot), ordem cronológica."""
    out: list[dict[str, Any]] = []
    for item in reversed(recent):
        if item.get("is_bot"):
            continue
        text = str(item.get("text") or "").strip()
        if not _is_substantive(text):
            continue
        out.append(item)
        if len(out) >= max(1, k):
            break
    out.reverse()
    return tuple(out)


def infer_dominant_topic(messages: tuple[dict[str, Any], ...]) -> str | None:
    """Tópico dominante no window — mensagens mais recentes pesam mais."""
    scores: dict[str, float] = {}
    n = len(messages)
    for i, item in enumerate(messages):
        text = str(item.get("text") or "").lower()
        weight = 1.0 + (i / max(n, 1))  # mais recente = maior peso
        for topic, markers in _TOPIC_PATTERNS:
            if any(m in text for m in markers):
                scores[topic] = scores.get(topic, 0.0) + weight
    if not scores:
        return None
    return max(scores.items(), key=lambda x: x[1])[0]


def expand_academic_shorthand(query: str) -> str:
    """Expande TP/AT/prova para retrieval (não altera mensagem ao utilizador)."""
    out = query or ""
    for pattern, replacement in _ACADEMIC_SHORTHAND:
        out = pattern.sub(replacement, out)
    return out.strip()


def strip_urls_from_query(query: str) -> str:
    """URLs não entram como termos BM25 — ficam só fora da query."""
    return _URL_RE.sub("", query or "").strip()


def resolve_query_from_recent(
    user_message: str,
    recent: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    *,
    k: int = 4,
) -> ResolvedConversationQuery:
    """Resolve dêiticos/ambiguidade usando janela K (default 4)."""
    original = (user_message or "").strip()
    if not is_deictic_or_ambiguous_query(original):
        resolved = expand_academic_shorthand(strip_urls_from_query(original))
        return ResolvedConversationQuery(
            original=original,
            resolved=resolved or original,
            was_resolved=False,
            resolution_k=0,
            dominant_topic=infer_dominant_topic(select_recent_window(recent, k=k)),
            ambiguous_unresolved=False,
        )

    window = select_recent_window(recent, k=k)
    if not window:
        return ResolvedConversationQuery(
            original=original,
            resolved=original,
            was_resolved=False,
            resolution_k=0,
            dominant_topic=None,
            ambiguous_unresolved=True,
            reason="no_substantive_recent_context",
        )

    topic = infer_dominant_topic(window)
    anchor = _resolution_anchor(window, topic)

    parts: list[str] = []
    if topic:
        parts.append(topic)
    if anchor:
        parts.append(anchor)
    parts.append(original)
    resolved = expand_academic_shorthand(strip_urls_from_query(" ".join(parts)))
    resolved = resolved[:500].strip()

    return ResolvedConversationQuery(
        original=original,
        resolved=resolved or original,
        was_resolved=True,
        resolution_k=len(window),
        dominant_topic=topic,
        ambiguous_unresolved=False,
    )


def detect_social_conflict(
    recent: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> SocialConflictHint | None:
    """Detecta divergência social sobre prova (ex.: terça vs quarta)."""
    days: list[str] = []
    for item in recent:
        if item.get("is_bot"):
            continue
        text = str(item.get("text") or "").strip()
        if not _ACADEMIC_EVENT_RE.search(text):
            continue
        for m in _DAY_RE.finditer(text):
            days.append(_normalize_day(m.group(1)))

    unique_days = sorted(set(days))
    if len(unique_days) < 2:
        return None

    note = (
        "## Aviso — informação conflitante no grupo\n"
        "Participantes mencionaram datas diferentes para a prova "
        f"({', '.join(unique_days)}). "
        "Priorize a agenda académica oficial e o material indexado; "
        "mencione a divergência e sugira confirmar com o responsável."
    )
    return SocialConflictHint(
        topic="prova",
        variants=tuple(unique_days),
        prompt_note=note,
    )


def _resolution_anchor(window: tuple[dict[str, Any], ...], topic: str | None) -> str:
    """Texto âncora: só mensagens alinhadas ao tópico dominante (anti-leakage)."""
    if not window:
        return ""
    if topic:
        markers = next((m for t, m in _TOPIC_PATTERNS if t == topic), ())
        matched: list[str] = []
        for item in window:
            text = str(item.get("text") or "").strip()
            if text and any(m in text.lower() for m in markers):
                matched.append(text)
        if matched:
            return " ".join(matched[-2:])
    return str(window[-1].get("text") or "").strip()


def needs_media_abstention(
    user_message: str,
    recent: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    *,
    quoted_context: str | None = None,
) -> bool:
    """True quando pergunta sobre conteúdo visual não disponível como texto."""
    msg = re.sub(r"@orbit\s*", "", (user_message or ""), flags=re.IGNORECASE).strip().lower()
    visual_ask = any(
        p in msg
        for p in (
            "o que é isso",
            "o que e isso",
            "what is this",
            "nesse print",
            "na imagem",
            "na foto",
            "no print",
            "olha isso",
            "veja isso",
        )
    ) or bool(re.search(r"\b(isso|isto)\b.*\?", msg))

    if not visual_ask:
        return False

    if quoted_context and is_media_placeholder(quoted_context):
        return True

    for item in reversed(recent):
        if item.get("is_bot"):
            continue
        text = str(item.get("text") or "").strip()
        if is_media_placeholder(text):
            return True
        if _is_substantive(text):
            return False

    return False


MEDIA_ABSTENTION_BLOCK = (
    "## Restrição — conteúdo visual não interpretado\n"
    "A mensagem referencia imagem/mídia sem transcrição disponível. "
    "NÃO descreva nem invente o que aparece na mídia. "
    "Peça ao utilizador que descreva por texto ou envie o conteúdo relevante. "
    "Tom: directo e curto, sem emojis."
)

THREAD_UNCLEAR_BLOCK = (
    "## Ambiguidade de thread\n"
    "A pergunta é ambígua e o contexto recente não permite identificar "
    "a qual discussão se refere. Peça esclarecimento em vez de assumir um tópico. "
    "Tom: directo e curto, sem emojis nem formalidade corporativa."
)
