#!/usr/bin/env python3
"""Smoke test do frontend (Playwright Python — evita conflito npm/lightningcss)."""
from __future__ import annotations

import json
import re
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = __import__("os").environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8001")

SKIP_INTRO_JS = """() => {
    try { sessionStorage.setItem('kernel_intro_seen', '1'); } catch (_) {}
    document.querySelectorAll('.entrance-init-hidden').forEach((el) => {
        el.classList.remove('entrance-init-hidden');
    });
}"""


def skip_entrance_animation(page) -> None:
    page.evaluate(SKIP_INTRO_JS)


def wait_for_chat_input(page, timeout: float = 15000) -> None:
    page.locator("#message-input").wait_for(state="visible", timeout=timeout)


def check_public_config() -> list[tuple[str, bool]]:
    checks: list[tuple[str, bool]] = []
    try:
        with urllib.request.urlopen(f"{BASE}/api/public-config", timeout=10) as resp:
            data = json.loads(resp.read().decode())
        checks.append((
            "public-config ISS base",
            bool(data.get("iss_lesson_base", "").startswith("http")),
        ))
        checks.append((
            "public-config catalog_enabled",
            "catalog_enabled" in data and isinstance(data["catalog_enabled"], bool),
        ))
    except Exception:
        checks.append(("public-config ISS base", False))
        checks.append(("public-config catalog_enabled", False))
    return checks


def resolve_browsers() -> list[str]:
    raw = __import__("os").environ.get("SMOKE_BROWSERS") or __import__("os").environ.get(
        "SMOKE_BROWSER", "chromium"
    )
    names = [b.strip().lower() for b in raw.split(",") if b.strip()]
    return names or ["chromium"]


def launch_browser(playwright, name: str):
    if name == "firefox":
        return playwright.firefox.launch(headless=True)
    if name == "webkit":
        return playwright.webkit.launch(headless=True)
    if name in ("msedge", "edge"):
        return playwright.chromium.launch(channel="msedge", headless=True)
    if name == "chrome":
        return playwright.chromium.launch(channel="chrome", headless=True)
    return playwright.chromium.launch(headless=True)


def smoke_silo_pill_deep_link(page, prefix: str) -> dict[str, object]:
    page.goto(f"{BASE}/?d=python", wait_until="networkidle")
    skip_entrance_animation(page)
    wait_for_chat_input(page)
    input_ok = page.locator("#message-input").input_value().startswith("/python")
    pill_ok = page.locator("#silo-pill:not([hidden])").is_visible()
    return {
        "check": prefix + "T9 silo-pill deep link",
        "ok": input_ok and pill_ok,
    }


def smoke_low_grounding_banner(page, prefix: str) -> dict[str, object]:
    ok = page.evaluate(
        """async () => {
        const mod = await import('/src/components/MessageRow.js');
        const el = document.createElement('div');
        mod.mountLowGroundingNotice(el, { confidence: 'low', sources: [] });
        return el.querySelector('.message-low-grounding-banner') !== null;
    }"""
    )
    return {"check": prefix + "T10 low-grounding banner", "ok": bool(ok)}


def smoke_delete_undo(page, prefix: str) -> dict[str, object]:
    page.evaluate(
        """() => {
        const now = Date.now();
        localStorage.setItem('kernel_conversations_v2', JSON.stringify({
            activeId: 'undo-a',
            conversations: [
                { id: 'undo-a', title: 'Manter', createdAt: 1, updatedAt: 1,
                  session_id: 'sa', disciplineId: null,
                  turns: [{ role: 'user', text: 'pergunta manter', ts: now }] },
                { id: 'undo-b', title: 'Apagar', createdAt: 2, updatedAt: 2,
                  session_id: 'sb', disciplineId: null,
                  turns: [{ role: 'user', text: 'pergunta apagar', ts: now }] },
            ],
        }));
    }"""
    )
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector(".conversation-sidebar__item-wrap", timeout=15000)

    target = page.locator(".conversation-sidebar__item-wrap", has_text="Apagar")
    target.hover()
    target.locator(".conversation-sidebar__menu-trigger").click()
    page.get_by_role("menuitem", name="Excluir").click()
    page.get_by_role("button", name="Sim").click()

    toast_action = page.locator(".toast__action", has_text="Desfazer")
    toast_action.wait_for(state="visible", timeout=5000)
    toast_action.click()

    restored = page.locator(".conversation-sidebar__item-wrap", has_text="Apagar").count() == 1
    return {"check": prefix + "T11 delete undo toast", "ok": restored}


def smoke_streaming_feedback(page, prefix: str) -> dict[str, object]:
    page.goto(BASE, wait_until="domcontentloaded")
    skip_entrance_animation(page)
    wait_for_chat_input(page)

    def _hang_chat(route) -> None:
        """Mantém POST /chat pendente para o estado streaming permanecer visível."""
        return

    page.route("**/chat", _hang_chat)

    page.locator("#message-input").fill("teste smoke streaming")
    page.locator("#send-button").click()
    page.locator("#send-button.send-button--streaming").wait_for(state="visible", timeout=500)
    busy = page.locator("#message-input[aria-busy='true']").count() == 1
    try:
        page.locator("#send-button.send-button--streaming").click(timeout=1000)
    except Exception:
        pass
    page.unroute("**/chat", _hang_chat)
    return {"check": prefix + "T12 streaming feedback", "ok": busy}


def smoke_mobile_layout(page, prefix: str) -> dict[str, object]:
    viewports = [(390, 844), (375, 812), (320, 568)]
    overflow_ok = True
    pills_balanced = True

    for width, height in viewports:
        page.set_viewport_size({"width": width, "height": height})
        page.goto(BASE, wait_until="domcontentloaded")
        skip_entrance_animation(page)
        page.wait_for_selector(".entrance-discipline-pills .cmd-pill", timeout=15000)

        has_overflow = page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"
        )
        if has_overflow:
            overflow_ok = False

        if width == 390:
            pills_balanced = page.evaluate(
                """() => {
                const pills = [...document.querySelectorAll('.entrance-discipline-pills .cmd-pill')];
                if (pills.length < 5) return false;
                const rows = new Map();
                for (const el of pills) {
                    const y = Math.round(el.getBoundingClientRect().top);
                    rows.set(y, (rows.get(y) || 0) + 1);
                }
                const counts = [...rows.values()];
                if (counts.length !== 2) return false;
                return counts[0] === 3 && counts[1] === 2;
            }"""
            )

    page.set_viewport_size({"width": 1280, "height": 720})
    return {
        "check": prefix + "F4 mobile layout pills+overflow",
        "ok": overflow_ok and pills_balanced,
    }


def _seed_sidebar_conversations(page) -> None:
    page.evaluate(
        """() => {
        const now = Date.now();
        localStorage.setItem('kernel_conversations_v2', JSON.stringify({
            activeId: 'menu-a',
            conversations: [
                { id: 'menu-a', title: 'Conversa Menu', createdAt: 1, updatedAt: 1,
                  session_id: 'sm1', disciplineId: null,
                  turns: [{ role: 'user', text: 'teste menu', ts: now }] },
            ],
        }));
        try { sessionStorage.setItem('kernel_intro_seen', '1'); } catch (_) {}
    }"""
    )


def smoke_sidebar_menu_a11y(page, prefix: str) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    _seed_sidebar_conversations(page)
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(BASE, wait_until="domcontentloaded")
    skip_entrance_animation(page)
    page.wait_for_selector(".conversation-sidebar__item-wrap", timeout=15000)

    row = page.locator(".conversation-sidebar__item-wrap", has_text="Conversa Menu")
    row.hover()
    row.locator(".conversation-sidebar__menu-trigger").click()
    page.get_by_role("menuitem", name="Renomear").click()
    rename_visible = page.locator(".conversation-sidebar__rename-input").is_visible()
    checks.append({"check": prefix + "T15 menuitem Renomear", "ok": rename_visible})

    page.keyboard.press("Escape")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector(".conversation-sidebar__item-wrap", timeout=15000)

    row = page.locator(".conversation-sidebar__item-wrap", has_text="Conversa Menu")
    trigger = row.locator(".conversation-sidebar__menu-trigger")
    trigger.focus()
    page.keyboard.press("Enter")
    page.keyboard.press("ArrowDown")
    focused_excluir = page.evaluate(
        """() => {
        const el = document.activeElement;
        return el?.getAttribute('role') === 'menuitem'
            && (el.textContent || '').trim() === 'Excluir';
    }"""
    )
    checks.append({"check": prefix + "T15 menu keyboard nav", "ok": bool(focused_excluir)})

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(BASE, wait_until="domcontentloaded")
    skip_entrance_animation(page)
    page.locator("#sidebar-toggle").click()
    page.wait_for_selector(".conversation-sidebar--open", timeout=5000)
    touch_visible = page.evaluate(
        """() => {
        const trigger = document.querySelector('.conversation-sidebar__menu-trigger');
        if (!trigger) return false;
        const style = getComputedStyle(trigger);
        return parseFloat(style.opacity) >= 0.99 && style.pointerEvents !== 'none';
    }"""
    )
    checks.append({"check": prefix + "T16 menu trigger touch visible", "ok": bool(touch_visible)})

    page.set_viewport_size({"width": 1280, "height": 720})
    return checks


def smoke_residual_flows(page, prefix: str) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []

    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(BASE, wait_until="domcontentloaded")
    skip_entrance_animation(page)

    note = page.locator("#sidebar-storage-note")
    note_text = note.text_content(timeout=5000) or ""
    checks.append({
        "check": prefix + "T23 storage note",
        "ok": note.is_visible() and "limpar dados" in note_text.lower(),
    })

    wait_for_chat_input(page)

    def _hang_chat(route) -> None:
        return

    page.route("**/chat", _hang_chat)
    page.locator("#message-input").fill("parar teste smoke")
    page.locator("#send-button").click()
    page.locator("#send-button.send-button--streaming").wait_for(state="visible", timeout=500)
    page.locator("#send-button.send-button--streaming").click()
    page.wait_for_function(
        "() => !document.querySelector('#send-button.send-button--streaming')",
        timeout=5000,
    )
    checks.append({
        "check": prefix + "T24 stop generation",
        "ok": page.locator("#send-button.send-button--streaming").count() == 0,
    })
    page.unroute("**/chat", _hang_chat)

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(BASE, wait_until="domcontentloaded")
    skip_entrance_animation(page)
    page.locator("#sidebar-toggle").click()
    checks.append({
        "check": prefix + "T24 sidebar mobile",
        "ok": page.locator("#conversation-sidebar.conversation-sidebar--open").count() == 1,
    })

    page.set_viewport_size({"width": 1280, "height": 720})
    page.evaluate("() => { try { localStorage.removeItem('kernel_sidebar_collapsed'); } catch (_) {} }")
    page.goto(BASE, wait_until="domcontentloaded")
    skip_entrance_animation(page)
    page.locator("#sidebar-collapse-toggle").click()
    checks.append({
        "check": prefix + "T24 sidebar collapse",
        "ok": page.locator("#conversation-sidebar.conversation-sidebar--collapsed").count() == 1,
    })

    page.set_viewport_size({"width": 1280, "height": 720})
    return checks


def smoke_theme_consistency(page, prefix: str) -> list[dict[str, object]]:
    page.evaluate(
        """() => {
        try { localStorage.setItem('kernel-theme', 'dark'); } catch (_) {}
    }"""
    )
    page.goto(BASE, wait_until="domcontentloaded")
    skip_entrance_animation(page)

    toggle = page.locator("#theme-toggle")
    dark_label = toggle.get_attribute("aria-label") or ""
    toggle.click()
    light_label = toggle.get_attribute("aria-label") or ""
    labels_ok = dark_label == "Ativar tema claro" and light_label == "Ativar tema escuro"

    page.reload(wait_until="domcontentloaded")
    persisted_light = page.evaluate(
        "() => document.documentElement.getAttribute('data-theme') === 'light'"
    )

    page.locator("#theme-toggle").click()
    page.reload(wait_until="domcontentloaded")
    persisted_dark = page.evaluate(
        "() => !document.documentElement.hasAttribute('data-theme')"
    )

    eyebrow_ok = page.evaluate(
        """() => {
        const text = document.querySelector('.entrance-eyebrow')?.textContent || '';
        return /assistente de estudo/i.test(text);
    }"""
    )

    return [
        {"check": prefix + "T18 theme aria-label", "ok": labels_ok},
        {"check": prefix + "T18 theme localStorage", "ok": persisted_light and persisted_dark},
        {"check": prefix + "T17 product eyebrow", "ok": eyebrow_ok},
    ]


def main() -> int:
    results: list[dict[str, object]] = []

    for label, ok in check_public_config():
        results.append({"check": label, "ok": ok})

    browsers = resolve_browsers()

    with sync_playwright() as p:
        for browser_name in browsers:
            browser = launch_browser(p, browser_name)
            page = browser.new_page()
            prefix = f"[{browser_name}] "
            try:
                page.goto(BASE, wait_until="networkidle", timeout=30000)

                page.wait_for_function(
                    """() => /disciplinas/i.test(
                        document.querySelector('.entrance-title-text')?.textContent || ''
                    )""",
                    timeout=15000,
                )

                hero = page.locator(".entrance-title-text").text_content(timeout=15000) or ""
                results.append({
                    "check": prefix + "T5 hero",
                    "ok": bool(re.search(r"disciplinas", hero, re.I)),
                })

                pill_count = page.locator(".entrance-discipline-pills .cmd-pill").count()
                results.append({"check": prefix + "T4 pills", "ok": pill_count >= 5})

                results.append({
                    "check": prefix + "T1 notice hidden empty",
                    "ok": page.locator("#context-window-notice").is_hidden(),
                })

                page.evaluate(
                    """() => {
                    try { sessionStorage.setItem('kernel_intro_seen', '1'); } catch (_) {}
                    const turns = [];
                    for (let i = 0; i < 13; i++) {
                        turns.push({ role: "user", text: `q${i}`, ts: Date.now() });
                        turns.push({ role: "bot", text: `a${i}`, ts: Date.now() });
                    }
                    localStorage.setItem(
                        "kernel_conversations_v2",
                        JSON.stringify({
                            activeId: "test",
                            conversations: [{
                                id: "test", title: "Test", createdAt: 0, updatedAt: 0,
                                session_id: "x", turns
                            }],
                        }),
                    );
                }"""
                )
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function(
                    "() => document.querySelectorAll('.message-row').length >= 1",
                    timeout=20000,
                )
                page.wait_for_function(
                    "() => document.body.classList.contains('chat-active')",
                    timeout=15000,
                )
                skip_entrance_animation(page)
                results.append({
                    "check": prefix + "T1 notice with 26 turns",
                    "ok": page.locator("#context-window-notice").is_visible(),
                })

                wait_for_chat_input(page)
                page.locator("#message-input").fill("/py")
                page.wait_for_timeout(300)
                results.append({
                    "check": prefix + "T3 slash menu",
                    "ok": page.locator("#slash-command-menu:not([hidden])").is_visible(),
                })

                results.append(smoke_silo_pill_deep_link(page, prefix))
                results.append(smoke_low_grounding_banner(page, prefix))
                results.append(smoke_delete_undo(page, prefix))
                results.append(smoke_streaming_feedback(page, prefix))
                results.append(smoke_mobile_layout(page, prefix))
                results.extend(smoke_sidebar_menu_a11y(page, prefix))
                results.extend(smoke_theme_consistency(page, prefix))
                results.extend(smoke_residual_flows(page, prefix))

                page.goto(BASE, wait_until="networkidle")
                results.append({
                    "check": prefix + "T10 sidebar",
                    "ok": page.locator("#conversation-sidebar").count() == 1,
                })

                iss_base = page.evaluate(
                    """async () => {
                    const r = await fetch('/api/public-config');
                    if (!r.ok) return '';
                    const j = await r.json();
                    return j.iss_lesson_base || '';
                }"""
                )
                results.append({
                    "check": prefix + "ISS config fetch in page",
                    "ok": str(iss_base).startswith("http"),
                })
            finally:
                browser.close()

    print(json.dumps(results, indent=2, ensure_ascii=False))
    failed = [r for r in results if not r["ok"]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
