"""
Scraping autenticado com navegação multi-etapa e download de .vtt do Google Drive.

Fluxo:
  Login → menu link → card → link → accordions → botão de transcrição → Google Drive (.vtt)

ADAPTE os seletores na seção SELECTORS para os elementos do seu site.
Use --no-headless para ver o browser e inspecionar os elementos com F12.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

import httpx
from playwright.async_api import BrowserContext, Page, async_playwright


# ─── Adapte estes seletores ao site alvo ─────────────────────────────────────
SELECTORS = {
    # Login
    "username_input":    "#user_login",
    "password_input":    "#user_pass",
    "submit_button":     "input[type=submit]",

    # Passo 2: link no menu principal (após login)
    "menu_link":         "#menu-item-76 > a",            # ex: "nav a[href*='cursos']"

    # Passo 3: card clicável na página seguinte
    "course_card":       "#groups-list > li.item-entry.odd.hidden.group-type-blocos850.is-member.group-has-avatar > div > div.item.group-join-button-hidden > div.group-item-wrap > div.item-block > h2 > a",             # ex: "div.course-card h2 a"

    # Passo 4: link que leva à página de módulos/aulas
    "module_link":       "#nav-infnet-ci-zoom-mettings",           # ex: "a[href*='modulo']"

    # Passo 5: botões que abrem os accordions (todos na página)
    "accordion_buttons": "#item-body > div > section > button", # ex: ".accordion button"

    # Passo 6: itens de aula dentro de cada accordion expandido
    "lesson_items":      "#item-body > div > section > div > div.infnetci-recordings-section > div",   # ex: ".accordion-content li"

    # Título da aula dentro do item (tenta vários seletores comuns)
    "lesson_title":      "h3, h4, strong",

    # Passo 7: botão de transcrição em cada item de aula
    "transcript_button": "a.recording-link.transcription-link",      # ex: "button[data-type='transcript']"
}
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ScrapedLesson:
    slug: str
    title: str
    order: int
    discipline: str  # extraído do texto do botão do accordion
    raw_text: str    # texto extraído e limpo do .vtt
    url: str         # URL do Google Drive (origem)


# ── Utilitários ──────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def _extract_order(title: str, fallback_index: int) -> int:
    m = re.search(r"(\d+)", title)
    return int(m.group(1)) if m else fallback_index


def _parse_vtt(content: str) -> str:
    """
    Remove cabeçalho WEBVTT, timestamps e tags HTML do conteúdo .vtt.
    Retorna apenas o texto falado, sem duplicatas de linhas adjacentes.

    Formato .vtt:
        WEBVTT

        00:00:00.000 --> 00:00:05.000
        Texto da fala aqui.
    """
    lines = content.splitlines()
    text_lines: list[str] = []
    last = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("WEBVTT") or line.startswith("NOTE"):
            continue
        # Linha de timestamp: "00:00:00.000 --> 00:00:05.000 ..."
        if re.match(r"^\d{2}:\d{2}[\d:,.]+\s*-->", line):
            continue
        # Remove tags HTML e timestamps inline como <c>, <00:00:00.000>
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line:
            continue
        # Evita duplicatas consecutivas (legendas repetidas em blocos seguidos)
        if line != last:
            text_lines.append(line)
            last = line

    return " ".join(text_lines)


def _gdrive_download_url(page_url: str) -> str | None:
    """
    Converte URL de visualização do Google Drive em URL de download direto.
    Ex: https://drive.google.com/file/d/FILE_ID/view
     →  https://drive.google.com/uc?export=download&id=FILE_ID
    """
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", page_url)
    if m:
        file_id = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    if "export=download" in page_url or page_url.endswith(".vtt"):
        return page_url
    return None


async def _download_vtt(context: BrowserContext, drive_url: str) -> str | None:
    """Baixa o conteúdo .vtt do Google Drive usando os cookies da sessão do Playwright."""
    download_url = _gdrive_download_url(drive_url)
    if not download_url:
        print(f"   ⚠  Não foi possível montar URL de download: {drive_url}")
        return None

    # Repassa os cookies do Playwright para o httpx (mantém autenticação Google)
    cookies = await context.cookies()
    cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            r = await client.get(
                download_url,
                headers={"Cookie": cookie_header},
            )
            r.raise_for_status()
            return r.text
    except Exception as exc:
        print(f"   ⚠  Falha ao baixar .vtt: {exc}")
        return None


# ── Scraper principal ─────────────────────────────────────────────────────────

async def scrape(
    site_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    limit: int | None = None,
    headless: bool = True,
    discipline_filter: str | None = None,
    skip_orders: dict[str, set[int]] | None = None,
) -> list[ScrapedLesson]:
    """
    Executa o fluxo completo de scraping e retorna lista de ScrapedLesson.
    Variáveis de ambiente usadas se parâmetros não fornecidos: SITE_URL, SITE_USER, SITE_PASS
    """
    site_url = site_url or os.environ["SITE_URL"]
    username = username or os.environ["SITE_USER"]
    password = password or os.environ["SITE_PASS"]

    lessons: list[ScrapedLesson] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context()
        page: Page = await context.new_page()

        # ── Passo 1: Login ─────────────────────────────────────────────────
        print("🔐  Fazendo login...")
        await page.goto(site_url, wait_until="domcontentloaded")
        await page.fill(SELECTORS["username_input"], username)
        await page.fill(SELECTORS["password_input"], password)
        await page.click(SELECTORS["submit_button"])
        # Aguarda a URL mudar (sai da página de login), sem depender de networkidle
        await page.wait_for_url(lambda url: "login" not in url.lower(), timeout=15_000)
        await page.wait_for_load_state("domcontentloaded")
        print(f"   ✅  Logado — {page.url}")

        # ── Passo 2: Clica no link do menu ─────────────────────────────────
        print("📂  Navegando pelo menu...")
        await page.click(SELECTORS["menu_link"])
        await page.wait_for_load_state("domcontentloaded")

        # ── Passo 3: Clica no card do curso ────────────────────────────────
        await page.click(SELECTORS["course_card"])
        await page.wait_for_load_state("domcontentloaded")

        # ── Passo 4: Clica no link de módulos ──────────────────────────────
        await page.click(SELECTORS["module_link"])
        await page.wait_for_load_state("domcontentloaded")
        print(f"   📄  Página de módulos: {page.url}")

        # ── Passos 5+6+7: accordion por vez (abrir um fecha o anterior) ────
        # Conta quantos accordions existem antes de começar
        acc_count = await page.locator(SELECTORS["accordion_buttons"]).count()
        print(f"   🗂   {acc_count} accordion(s) encontrado(s)")

        global_index = 0  # índice global de aula para fallback de ordem

        for acc_i in range(acc_count):
            if limit and len(lessons) >= limit:
                break

            # Re-busca os botões a cada iteração — DOM pode ter mudado
            btns = page.locator(SELECTORS["accordion_buttons"])
            btn = btns.nth(acc_i)

            discipline = (await btn.inner_text()).strip()

            if discipline_filter and discipline_filter.lower() not in discipline.lower():
                print(f"   ⏩  Pulando accordion {acc_i + 1}: {discipline!r}")
                continue

            print(f"\n   📂  Abrindo accordion {acc_i + 1}/{acc_count}: {discipline!r}...")
            await btn.scroll_into_view_if_needed()
            await btn.click()

            # Aguarda pelo menos um item de aula ficar visível neste accordion
            try:
                await page.wait_for_selector(
                    SELECTORS["lesson_items"],
                    state="visible",
                    timeout=8_000,
                )
            except Exception:
                print(f"   ⚠  Nenhum item visível no accordion {acc_i + 1} — pulando.")
                continue

            await page.wait_for_timeout(300)  # estabiliza animação

            all_items = await page.query_selector_all(SELECTORS["lesson_items"])
            lesson_items = [item for item in all_items if await item.is_visible()]
            print(f"   📚  {len(lesson_items)} aula(s) visível(is) neste accordion")

            for item in lesson_items:
                if limit and len(lessons) >= limit:
                    break

                title_el = await item.query_selector(SELECTORS["lesson_title"])
                title = (await title_el.inner_text()).strip() if title_el else f"Aula {global_index + 1}"
                order = _extract_order(title, global_index)

                if skip_orders and order in skip_orders.get(discipline, set()):
                    print(f"   ⏭  {title!r} (order={order}) — já existe no banco.")
                    global_index += 1
                    continue

                transcript_btn = await item.query_selector(SELECTORS["transcript_button"])
                if not transcript_btn:
                    print(f"   ⚠  Botão de transcrição não encontrado: {title!r}")
                    global_index += 1
                    continue

                print(f"\n   📥  Baixando transcrição: {title!r}...")

                # Garante visibilidade antes de clicar
                await transcript_btn.scroll_into_view_if_needed()

                # ── Passo 7: Clica e captura nova aba do Google Drive ──────
                async with context.expect_page() as new_page_info:
                    await transcript_btn.click(force=True)

                drive_page = await new_page_info.value
                await drive_page.wait_for_load_state("domcontentloaded")
                drive_url = drive_page.url
                await drive_page.close()

                print(f"   🔗  Drive URL: {drive_url}")

                vtt_content = await _download_vtt(context, drive_url)
                if not vtt_content:
                    global_index += 1
                    continue

                raw_text = _parse_vtt(vtt_content)
                if not raw_text.strip():
                    print(f"   ⚠  .vtt vazio após parsing: {title!r}")
                    global_index += 1
                    continue

                lessons.append(ScrapedLesson(
                    slug=_slugify(title),
                    title=title,
                    order=order,
                    discipline=discipline,
                    raw_text=raw_text,
                    url=drive_url,
                ))
                print(f"   ✅  {len(raw_text)} chars extraídos")
                global_index += 1

        await browser.close()

    return lessons
