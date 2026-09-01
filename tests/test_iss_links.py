"""URLs ISS para citações RAG."""

from __future__ import annotations

from kernel.knowledge.iss_links import (
    beautify_iss_citations_in_answer,
    build_source_citations,
    format_source_header,
    format_source_label,
    format_whatsapp_sources_block,
    iss_lesson_url,
    parse_db_source,
    replace_db_source_citations,
    slug_to_fallback_title,
    sources_to_public_urls,
    strip_user_facing_citations,
)

BASE = "https://gaabdevweb.github.io/ISS/public/aula.html"


def test_parse_db_source():
    assert parse_db_source("db:fundamentos-java/switch-menu-do-while-calculadora-java") == (
        "fundamentos-java",
        "switch-menu-do-while-calculadora-java",
    )
    assert parse_db_source("db:doc/x") == ("doc", "x")


def test_iss_lesson_url():
    url = iss_lesson_url("fundamentos-java", "raciocinio-codigo-primeiro-contato-java", BASE)
    assert url == (
        "https://gaabdevweb.github.io/ISS/public/aula.html"
        "?d=fundamentos-java&a=raciocinio-codigo-primeiro-contato-java"
    )


def test_format_source_label_db_to_url():
    src = "db:fundamentos-java/switch-menu-do-while-calculadora-java"
    assert format_source_label(src, BASE).startswith("https://")
    assert "fundamentos-java" in format_source_label(src, BASE)
    assert format_source_label("db:doc/manual", BASE) == "db:doc/manual"


def test_format_source_header():
    h = format_source_header(
        "db:fundamentos-csharp/desvio-condicional-if-else-switch-csharp",
        BASE,
        score=0.95,
    )
    assert h.startswith("[Fonte: https://")
    assert "Score: 0.95" in h


def test_replace_db_source_citations():
    text = (
        "Ver [Fonte: db:fundamentos-java/switch-menu-do-while-calculadora-java]\n"
        "Fonte: db:fundamentos-java/switch-menu-do-while-calculadora-java"
    )
    out = replace_db_source_citations(text, BASE)
    assert "db:fundamentos-java" not in out
    assert "gaabdevweb.github.io/ISS/public/aula.html" in out


def test_sources_to_public_urls_dedupes():
    urls = sources_to_public_urls(
        (
            "db:fundamentos-java/a",
            "db:fundamentos-java/a",
            "db:doc/x",
        ),
        BASE,
    )
    assert len(urls) == 1


def test_slug_to_fallback_title():
    assert slug_to_fallback_title("switch-menu-do-while-calculadora-java") == (
        "Switch Menu Do While Calculadora Java"
    )


def test_build_source_citations_with_details():
    citations = build_source_citations(
        ("db:fundamentos-java/switch-menu-do-while-calculadora-java",),
        BASE,
        (
            {
                "source": "db:fundamentos-java/switch-menu-do-while-calculadora-java",
                "lesson_title": "Menu calculadora Java",
                "discipline_label": "Fundamentos Java",
                "slug": "switch-menu-do-while-calculadora-java",
                "public_url": iss_lesson_url(
                    "fundamentos-java",
                    "switch-menu-do-while-calculadora-java",
                    BASE,
                ),
            },
        ),
    )
    assert len(citations) == 1
    assert citations[0]["title"] == "Menu calculadora Java"
    assert citations[0]["discipline_label"] == "Fundamentos Java"


def test_format_whatsapp_sources_block():
    url = iss_lesson_url("fundamentos-java", "switch-menu-do-while-calculadora-java", BASE)
    block = format_whatsapp_sources_block(
        [{"title": "Menu calculadora Java", "url": url, "discipline_label": "Fundamentos Java"}]
    )
    assert "📚 *Material de referência*" in block
    assert "*Menu calculadora Java*" in block
    assert "_Fundamentos Java_" in block
    assert url in block


def test_beautify_iss_citations_in_answer():
    url = iss_lesson_url("fundamentos-java", "switch-menu-do-while-calculadora-java", BASE)
    text = f"Ver detalhes.\nFonte: {url}"
    citations = [
        {
            "title": "Menu calculadora Java",
            "url": url,
            "discipline_label": "Fundamentos Java",
            "slug": "switch-menu-do-while-calculadora-java",
        }
    ]
    out = beautify_iss_citations_in_answer(text, BASE, citations)
    assert "Fonte:" not in out
    assert "*Menu calculadora Java*" in out
    assert url in out


def test_replace_db_source_citations_beautifies():
    src = "db:fundamentos-java/switch-menu-do-while-calculadora-java"
    text = f"Ver [Fonte: {src}]\nFonte: {src}"
    out = replace_db_source_citations(text, BASE)
    assert "db:fundamentos-java" not in out
    assert "📖 *Switch Menu Do While Calculadora Java*" in out


def test_strip_user_facing_citations_removes_all_visible_sources():
    url = iss_lesson_url("fundamentos-java", "classes-projetos-calculadora-media-java", BASE)
    text = (
        f"[📖 Classes e projetos práticos\n"
        f"Fundamentos Java\n"
        f"{url} | Score: 1.00]\n"
        f"Título: Classes e projetos práticos\n\n"
        f"Classes em Java são plantas.\n\n"
        f"1. Separação de projetos.\n"
        f"    📖 Classes e projetos práticos\n"
        f"Fundamentos Java\n"
        f"{url}\n\n"
        f"2. Escopo de variáveis.\n"
        f"Fonte: {url}\n\n"
        f"📚 *Material de referência*\n\n"
        f"• *Menu calculadora Java*\n"
        f"_{url}_"
    )
    out = strip_user_facing_citations(text)
    assert "gaabdevweb.github.io" not in out
    assert "📖" not in out
    assert "Fonte:" not in out
    assert "Material de referência" not in out
    assert "Título:" not in out
    assert "Score:" not in out
    assert "Classes em Java são plantas." in out
    assert "Escopo de variáveis." in out
