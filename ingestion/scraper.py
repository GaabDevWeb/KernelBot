"""
Scraping autenticado do site de aulas via Playwright.

Adapte as constantes SELECTORS e o método _list_lessons para o site específico.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from playwright.async_api import async_playwright

# ─── Adapte estes seletores ao site alvo ─────────────────────────────────────
SELECTORS = {
    "username_input":    "#email",           # campo de e-mail/usuário
    "password_input":    "#password",        # campo de senha
    "submit_button":     "button[type=submit]",
    "lesson_links":      "a.lesson-link",    # lista de aulas na página principal
    "transcript_area":   ".transcript-content",  # área de transcrição em cada aula
}
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ScrapedLesson:
    slug: str
    title: str
    order: int
    raw_text: str
    url: str


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text)


def _extract_order(title: str, url: str) -> int:
    """Tenta extrair número de ordem a partir do título ou URL."""
    for source in (title, url):
        m = re.search(r"(\d+)", source)
        if m:
            return int(m.group(1))
    return 0


async def scrape(
    site_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    limit: int | None = None,
    headless: bool = True,
) -> list[ScrapedLesson]:
    """
    Autentica no site, lista aulas e extrai transcrições.

    Parâmetros lidos de variáveis de ambiente se não fornecidos:
      SITE_URL, SITE_USER, SITE_PASS
    """
    site_url = site_url or os.environ["SITE_URL"]
    username = username or os.environ["SITE_USER"]
    password = password or os.environ["SITE_PASS"]

    lessons: list[ScrapedLesson] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        # ── Login ──────────────────────────────────────────────────────────
        await page.goto(site_url)
        await page.fill(SELECTORS["username_input"], username)
        await page.fill(SELECTORS["password_input"], password)
        await page.click(SELECTORS["submit_button"])
        await page.wait_for_load_state("networkidle")

        # ── Lista de aulas ─────────────────────────────────────────────────
        lesson_elements = await page.query_selector_all(SELECTORS["lesson_links"])
        lesson_items = []
        for el in lesson_elements:
            href = await el.get_attribute("href")
            title = (await el.inner_text()).strip()
            if href:
                lesson_items.append((title, href))

        if limit:
            lesson_items = lesson_items[:limit]

        # ── Extração de transcrições ───────────────────────────────────────
        for title, href in lesson_items:
            url = href if href.startswith("http") else site_url.rstrip("/") + href
            await page.goto(url)
            await page.wait_for_load_state("networkidle")

            transcript_el = await page.query_selector(SELECTORS["transcript_area"])
            if not transcript_el:
                print(f"⚠  Transcrição não encontrada: {title!r} ({url})")
                continue

            raw_text = (await transcript_el.inner_text()).strip()
            if not raw_text:
                print(f"⚠  Transcrição vazia: {title!r}")
                continue

            slug = _slugify(title)
            order = _extract_order(title, href)

            lessons.append(ScrapedLesson(
                slug=slug,
                title=title,
                order=order,
                raw_text=raw_text,
                url=url,
            ))
            print(f"📄  Coletado: {title!r} ({len(raw_text)} chars)")

        await browser.close()

    return lessons
