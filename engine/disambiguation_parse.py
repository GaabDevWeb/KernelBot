"""Parse de opções de desambiguação emitidas pelo LLM (XML ou JSON)."""

from __future__ import annotations

import json
import re
from xml.etree import ElementTree as ET

_AMBIGUITY_XML_RE = re.compile(
    r"<ambiguity_options\b[^>]*>(.*?)</ambiguity_options>",
    re.IGNORECASE | re.DOTALL,
)
_AMBIGUITY_JSON_RE = re.compile(
    r'\{\s*"disambiguation_options"\s*:\s*\[',
    re.IGNORECASE,
)
_INCOMPLETE_TAG_RE = re.compile(r"<ambiguity_options\b[^>]*>[\s\S]*$", re.IGNORECASE)
_PARTIAL_OPEN_RE = re.compile(r"<(?:/?ambiguity(?:_options)?)?$", re.IGNORECASE)


def _option_elem_to_dict(elem: ET.Element) -> dict[str, str] | None:
    discipline = (elem.get("discipline") or "").strip()
    slug = (elem.get("slug") or "").strip()
    label = (elem.get("label") or elem.get("title") or "").strip()
    if not label and not slug:
        return None
    return {
        "title": label or slug,
        "discipline": discipline,
        "slug": slug,
    }


def _normalize_option_dict(raw: object) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    discipline = str(raw.get("discipline") or "").strip()
    slug = str(raw.get("slug") or "").strip()
    label = str(raw.get("label") or raw.get("title") or "").strip()
    if not label and not slug:
        return None
    return {"title": label or slug, "discipline": discipline, "slug": slug}


def parse_ambiguity_options(text: str) -> list[dict[str, str]]:
    """Extrai candidatos de `<ambiguity_options>` ou JSON `disambiguation_options`."""
    if not text:
        return []

    out: list[dict[str, str]] = []

    for block in _AMBIGUITY_XML_RE.findall(text):
        try:
            root = ET.fromstring(f"<ambiguity_options>{block}</ambiguity_options>")
        except ET.ParseError:
            continue
        for child in root:
            if child.tag.lower() != "option":
                continue
            item = _option_elem_to_dict(child)
            if item:
                out.append(item)

    if out:
        return out

    for match in _AMBIGUITY_JSON_RE.finditer(text):
        start = match.start()
        snippet = text[start:]
        try:
            payload = json.loads(snippet)
        except json.JSONDecodeError:
            depth = 0
            end = None
            for i, ch in enumerate(snippet):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end is None:
                continue
            try:
                payload = json.loads(snippet[:end])
            except json.JSONDecodeError:
                continue
        else:
            pass
        options = payload.get("disambiguation_options") if isinstance(payload, dict) else None
        if isinstance(options, list):
            for raw in options:
                item = _normalize_option_dict(raw)
                if item:
                    out.append(item)
        if out:
            return out

    return out


_OPTION_SELF_CLOSE_RE = re.compile(r"<option\b([^>]*?)\s*/>", re.IGNORECASE)
_OPTION_PAIR_CLOSE_RE = re.compile(r"<option\b([^>]*?)>\s*</option>", re.IGNORECASE)


def _parse_complete_options_from_fragment(fragment: str) -> list[dict[str, str]]:
    """Opções com fecho completo (`/>` ou `></option>`) dentro de um fragmento."""
    out: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    seen_starts: set[int] = set()
    for pattern in (_OPTION_SELF_CLOSE_RE, _OPTION_PAIR_CLOSE_RE):
        for om in pattern.finditer(fragment):
            if om.start() in seen_starts:
                continue
            seen_starts.add(om.start())
            attrs = om.group(1)
            if not _option_attrs_well_formed(attrs):
                continue
            discipline = _attr_from_option(attrs, "discipline")
            slug = _attr_from_option(attrs, "slug")
            label = _attr_from_option(attrs, "label") or _attr_from_option(attrs, "title")
            if not label and not slug:
                continue
            key = f"{discipline}:{slug}:{label}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            out.append({"title": label or slug, "discipline": discipline, "slug": slug})
    return out


def parse_incomplete_ambiguity_options(text: str) -> list[dict[str, str]]:
    """Extrai `<option>` de bloco `<ambiguity_options>` sem tag de fecho (stream cortado)."""
    if not text:
        return []
    m = re.search(r"<ambiguity_options\b[^>]*>", text, re.IGNORECASE)
    if not m:
        return []
    if re.search(r"</ambiguity_options>", text[m.end() :], re.IGNORECASE):
        return []
    fragment = text[m.start() :]
    complete = _parse_complete_options_from_fragment(fragment)
    if complete:
        return complete
    out: list[dict[str, str]] = []
    for om in re.finditer(r"<option\b([^>]*)\/?>", fragment, re.IGNORECASE):
        attrs = om.group(1)
        if not _option_attrs_well_formed(attrs):
            continue
        discipline = _attr_from_option(attrs, "discipline")
        slug = _attr_from_option(attrs, "slug")
        label = _attr_from_option(attrs, "label") or _attr_from_option(attrs, "title")
        if label or slug:
            out.append({"title": label or slug, "discipline": discipline, "slug": slug})
    return out


def _option_attrs_well_formed(attrs: str) -> bool:
    """Rejeita `<option>` cortado a meio de atributo (aspas não fechadas)."""
    if not attrs or "<" in attrs:
        return False
    if re.search(r'=\s*"[^"]*$', attrs):
        return False
    if re.search(r"=\s*'[^']*$", attrs):
        return False
    return True


def _attr_from_option(attrs: str, name: str) -> str:
    m = re.search(
        rf'{name}\s*=\s*("([^"]*)"|\'([^\']*)\')',
        attrs,
        re.IGNORECASE,
    )
    if not m:
        return ""
    return (m.group(2) or m.group(3) or "").strip()


def strip_ambiguity_markup(text: str) -> tuple[str, list[dict[str, str]]]:
    """Remove bloco estruturado do texto visível e devolve candidatos normalizados."""
    options = parse_ambiguity_options(text)
    if not options:
        options = parse_incomplete_ambiguity_options(text)
    cleaned = _AMBIGUITY_XML_RE.sub("", text)
    cleaned = _strip_json_disambiguation(cleaned)
    cleaned = _INCOMPLETE_TAG_RE.sub("", cleaned)
    cleaned = _PARTIAL_OPEN_RE.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, options


def _strip_json_disambiguation(text: str) -> str:
    for match in _AMBIGUITY_JSON_RE.finditer(text):
        start = match.start()
        snippet = text[start:]
        end = None
        depth = 0
        for i, ch in enumerate(snippet):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = start + i + 1
                    break
        if end is not None:
            return text[:start] + text[end:]
    return text


def candidates_from_retrieval(
    selected: tuple | list,
) -> list[dict[str, str]]:
    """Fallback: candidatos a partir dos hits de retrieval (paths de fonte)."""
    out: list[dict[str, str]] = []
    for c in selected:
        source = ""
        if hasattr(c, "source"):
            source = str(c.source or "")
        elif isinstance(c, dict):
            source = str(c.get("source") or "")
        if not source:
            continue
        parts = source.replace("\\", "/").split("/")
        discipline = parts[0] if len(parts) >= 2 else ""
        slug = parts[-1].replace(".json", "") if parts else source
        title = slug.replace("-", " ").replace("__", " — ")
        out.append({"title": title, "discipline": discipline, "slug": slug})
    return out
