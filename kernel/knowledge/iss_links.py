"""URLs públicas ISS para fontes RAG (`db:disciplina/slug`)."""

from __future__ import annotations

import re
from urllib.parse import quote

from kernel.disciplines.disciplines import indexed_silo_ids

_DB_SOURCE_RE = re.compile(r"^db:([^/]+)/([^/\s\]]+)")
# [Fonte: …], [Fonte 1: …], Fonte: … (resposta do LLM)
_CITATION_DB_RE = re.compile(
    r"(\[Fonte(?:\s+\d+)?:\s*)(db:[^\]\|\n]+)([^\]]*\])",
    re.IGNORECASE,
)
_PLAIN_FONTE_DB_RE = re.compile(
    r"(Fonte:\s*)(db:[^\s\n\]]+)",
    re.IGNORECASE,
)
_ISS_PUBLIC_URL_RE = re.compile(
    r"https://gaabdevweb\.github\.io/ISS/public/aula\.html\?[^\s\n\]]+",
    re.IGNORECASE,
)
_PLAIN_FONTE_ISS_URL_RE = re.compile(
    r"(Fonte:\s*)(https://gaabdevweb\.github\.io/ISS/public/aula\.html\?[^\s\n\]]+)",
    re.IGNORECASE,
)
_BRACKET_FONTE_ISS_URL_RE = re.compile(
    r"\[Fonte(?:\s+\d+)?:\s*https://gaabdevweb\.github\.io/ISS/public/aula\.html\?[^\]\|\n]+\]",
    re.IGNORECASE,
)
_BRACKET_FONTE_ANY_RE = re.compile(
    r"\[Fonte(?:\s+\d+)?:[^\]]*\]",
    re.IGNORECASE | re.DOTALL,
)
_BRACKET_BOOK_ANY_RE = re.compile(
    r"\[📖[^\]]*\]",
    re.DOTALL,
)
_INLINE_BOOK_BLOCK_RE = re.compile(
    r"(?:^|\n)\s*📖[^\n]*(?:\n(?!\s*\d+\.)[^\n]*)*?(?:\nhttps://gaabdevweb\.github\.io/ISS[^\s\n]*)?",
    re.MULTILINE | re.IGNORECASE,
)
_MATERIAL_REF_BLOCK_RE = re.compile(
    r"(?:^|\n)\s*📚\s*\*Material de referência\*[\s\S]*",
    re.IGNORECASE,
)
_STANDALONE_ISS_URL_LINE_RE = re.compile(
    r"^\s*https://gaabdevweb\.github\.io/ISS/public/aula\.html\?[^\s\n]+(?:\s*\|\s*Score:\s*[\d.]+)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_TITULO_METADATA_LINE_RE = re.compile(
    r"^\s*Título:\s*.+\s*$",
    re.MULTILINE,
)
_SCORE_FRAGMENT_RE = re.compile(
    r"\s*\|\s*Score:\s*[\d.]+",
    re.IGNORECASE,
)
_COLLAPSE_BLANK_LINES_RE = re.compile(r"\n{3,}")


def parse_db_source(source: str) -> tuple[str, str] | None:
    """Extrai `(disciplina, slug)` de `db:disciplina/slug` ou com sufixo de chunk."""
    m = _DB_SOURCE_RE.match(str(source or "").strip())
    if not m:
        return None
    return m.group(1).strip().lower(), m.group(2).strip().lower()


def iss_lesson_url(discipline: str, slug: str, base_url: str) -> str:
    """Monta URL ISS: `{base}?d={discipline}&a={slug}`."""
    base = (base_url or "").strip().rstrip("?") or (
        "https://gaabdevweb.github.io/ISS/public/aula.html"
    )
    d = quote(discipline.strip(), safe="")
    a = quote(slug.strip(), safe="")
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}d={d}&a={a}"


def format_source_label(source: str, base_url: str) -> str:
    """Rótulo de fonte para prompt/resposta — URL ISS ou identificador original."""
    parsed = parse_db_source(source)
    if not parsed:
        return str(source or "").strip()
    disc, slug = parsed
    if disc not in indexed_silo_ids():
        return str(source or "").strip()
    if disc == "doc":
        return str(source or "").strip()
    return iss_lesson_url(disc, slug, base_url)


def format_source_header(
    source: str,
    base_url: str,
    *,
    index: int | None = None,
    score: float | None = None,
) -> str:
    """Cabeçalho `[Fonte: …]` injectado no prompt RAG."""
    label = format_source_label(source, base_url)
    if index is not None:
        if score is not None:
            return f"[Fonte {index}: {label} | Score: {score:.2f}]"
        return f"[Fonte {index}: {label}]"
    if score is not None:
        return f"[Fonte: {label} | Score: {score:.2f}]"
    return f"[Fonte: {label}]"


def slug_to_fallback_title(slug: str) -> str:
    """Título legível quando o catálogo não tem entrada."""
    clean = str(slug or "").strip().lower()
    if not clean:
        return "Aula"
    return " ".join(part.capitalize() for part in clean.replace("_", "-").split("-") if part)


def parse_iss_lesson_url(url: str) -> tuple[str, str] | None:
    """Extrai `(disciplina, slug)` de uma URL pública ISS."""
    from urllib.parse import parse_qs, urlparse

    raw = str(url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    qs = parse_qs(parsed.query)
    disc = (qs.get("d") or [""])[0].strip().lower()
    slug = (qs.get("a") or [""])[0].strip().lower()
    if not disc or not slug:
        return None
    return disc, slug


def build_source_citations(
    sources: tuple[str, ...] | list[str],
    base_url: str,
    source_details: tuple[dict, ...] | list[dict] | None = None,
) -> list[dict[str, str]]:
    """Citações enriquecidas para UI/WhatsApp: title, url, discipline_label."""
    details_by_source: dict[str, dict] = {}
    if source_details:
        for detail in source_details:
            src = str(detail.get("source") or "").strip()
            if src:
                details_by_source[src] = detail

    out: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for raw in sources:
        src = str(raw or "").strip()
        if not src:
            continue
        detail = details_by_source.get(src, {})
        url = str(detail.get("public_url") or format_source_label(src, base_url)).strip()
        if not url.startswith("http") or url in seen_urls:
            continue
        seen_urls.add(url)
        title = str(detail.get("lesson_title") or "").strip()
        slug = str(detail.get("slug") or "").strip()
        if not title:
            parsed = parse_db_source(src)
            slug = slug or (parsed[1] if parsed else "")
            title = slug_to_fallback_title(slug)
        disc_label = str(detail.get("discipline_label") or "").strip()
        out.append(
            {
                "title": title,
                "url": url,
                "discipline_label": disc_label,
                "slug": slug,
            }
        )
    return out


def format_whatsapp_source_entry(citation: dict[str, str]) -> str:
    """Uma fonte formatada para WhatsApp (*bold*, _italic_, URL numa linha)."""
    title = str(citation.get("title") or "Aula").strip()
    url = str(citation.get("url") or "").strip()
    disc = str(citation.get("discipline_label") or "").strip()
    lines = [f"• *{title}*"]
    if disc:
        lines.append(f"_{disc}_")
    if url:
        lines.append(url)
    return "\n".join(lines)


def format_whatsapp_sources_block(citations: list[dict[str, str]]) -> str:
    """Rodapé de referências para WhatsApp."""
    if not citations:
        return ""
    entries = [format_whatsapp_source_entry(c) for c in citations]
    return "📚 *Material de referência*\n\n" + "\n\n".join(entries)


def _citation_from_url(url: str, base_url: str) -> dict[str, str]:
    parsed = parse_iss_lesson_url(url)
    if not parsed:
        return {"title": "Aula", "url": url, "discipline_label": "", "slug": ""}
    disc, slug = parsed
    return {
        "title": slug_to_fallback_title(slug),
        "url": url,
        "discipline_label": disc.replace("-", " ").title(),
        "slug": slug,
    }


def format_inline_iss_citation(citation: dict[str, str]) -> str:
    """Citação inline compacta (substitui `Fonte: https://…`)."""
    title = str(citation.get("title") or "Aula").strip()
    url = str(citation.get("url") or "").strip()
    disc = str(citation.get("discipline_label") or "").strip()
    lines = [f"📖 *{title}*"]
    if disc:
        lines.append(f"_{disc}_")
    if url:
        lines.append(url)
    return "\n".join(lines)


def beautify_iss_citations_in_answer(
    text: str,
    base_url: str,
    citations: list[dict[str, str]] | None = None,
) -> str:
    """Substitui citações cruas `Fonte: https://…` por blocos legíveis."""
    by_url = {c["url"]: c for c in (citations or []) if c.get("url")}

    def _replace_plain_url(match: re.Match[str]) -> str:
        url = match.group(2).strip()
        citation = by_url.get(url) or _citation_from_url(url, base_url)
        return format_inline_iss_citation(citation)

    def _replace_bracket_url(match: re.Match[str]) -> str:
        url_match = _ISS_PUBLIC_URL_RE.search(match.group(0))
        if not url_match:
            return match.group(0)
        url = url_match.group(0)
        citation = by_url.get(url) or _citation_from_url(url, base_url)
        return format_inline_iss_citation(citation)

    out = _BRACKET_FONTE_ISS_URL_RE.sub(_replace_bracket_url, text or "")
    out = _PLAIN_FONTE_ISS_URL_RE.sub(_replace_plain_url, out)
    return out


def sources_to_public_urls(sources: tuple[str, ...] | list[str], base_url: str) -> list[str]:
    """Converte lista de sources internas em URLs ISS (dedupe, ordem preservada)."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in sources:
        label = format_source_label(str(raw), base_url)
        if label.startswith("http") and label not in seen:
            seen.add(label)
            out.append(label)
    return out


def replace_db_source_citations(
    text: str,
    base_url: str,
    citations: list[dict[str, str]] | None = None,
) -> str:
    """Substitui citações `db:…` por URLs ISS e formata citações legíveis."""

    def _bracket_repl(m: re.Match[str]) -> str:
        prefix, db_part, suffix = m.group(1), m.group(2).strip(), m.group(3)
        label = format_source_label(db_part, base_url)
        return f"{prefix}{label}{suffix}"

    def _plain_repl(m: re.Match[str]) -> str:
        prefix, db_part = m.group(1), m.group(2).strip()
        label = format_source_label(db_part, base_url)
        return f"{prefix}{label}"

    out = _CITATION_DB_RE.sub(_bracket_repl, text or "")
    out = _PLAIN_FONTE_DB_RE.sub(_plain_repl, out)
    return beautify_iss_citations_in_answer(out, base_url, citations)


def strip_user_facing_citations(text: str) -> str:
    """Remove citações, links ISS e blocos de referência da resposta ao utilizador."""
    out = str(text or "")
    out = _MATERIAL_REF_BLOCK_RE.sub("", out)
    out = _BRACKET_BOOK_ANY_RE.sub("", out)
    out = _BRACKET_FONTE_ANY_RE.sub("", out)
    out = _BRACKET_FONTE_ISS_URL_RE.sub("", out)
    out = _INLINE_BOOK_BLOCK_RE.sub("", out)
    out = _PLAIN_FONTE_ISS_URL_RE.sub("", out)
    out = _PLAIN_FONTE_DB_RE.sub("", out)
    out = _CITATION_DB_RE.sub("", out)
    out = _STANDALONE_ISS_URL_LINE_RE.sub("", out)
    out = _ISS_PUBLIC_URL_RE.sub("", out)
    out = _TITULO_METADATA_LINE_RE.sub("", out)
    out = _SCORE_FRAGMENT_RE.sub("", out)
    out = _COLLAPSE_BLANK_LINES_RE.sub("\n\n", out)
    return out.strip()
