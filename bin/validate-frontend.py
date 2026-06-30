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


def check_public_config() -> tuple[str, bool]:
    try:
        with urllib.request.urlopen(f"{BASE}/api/public-config", timeout=10) as resp:
            data = json.loads(resp.read().decode())
        ok = bool(data.get("iss_lesson_base", "").startswith("http"))
        return "public-config ISS base", ok
    except Exception as exc:
        return "public-config ISS base", False if not str(exc) else False


def main() -> int:
    results: list[dict[str, object]] = []

    label, ok = check_public_config()
    results.append({"check": label, "ok": ok})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(BASE, wait_until="networkidle", timeout=30000)

            page.wait_for_function(
                """() => /disciplinas/i.test(
                    document.querySelector('.entrance-title-text')?.textContent || ''
                )""",
                timeout=15000,
            )

            hero = page.locator(".entrance-title-text").text_content(timeout=15000) or ""
            results.append({"check": "T5 hero", "ok": bool(re.search(r"disciplinas", hero, re.I))})

            pill_count = page.locator(".entrance-discipline-pills .cmd-pill").count()
            results.append({"check": "T4 pills", "ok": pill_count >= 5})

            results.append({
                "check": "T1 notice hidden empty",
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
            page.reload(wait_until="networkidle")
            page.locator(".message-row").first.wait_for(state="attached", timeout=15000)
            page.wait_for_function(
                "() => document.body.classList.contains('chat-active')",
                timeout=15000,
            )
            skip_entrance_animation(page)
            results.append({
                "check": "T1 notice with 26 turns",
                "ok": page.locator("#context-window-notice").is_visible(),
            })

            wait_for_chat_input(page)
            # T3 slash menu — com histórico carregado o input está visível
            page.locator("#message-input").fill("/py")
            page.wait_for_timeout(300)
            results.append({
                "check": "T3 slash menu",
                "ok": page.locator("#slash-command-menu:not([hidden])").is_visible(),
            })

            page.goto(f"{BASE}/?d=python", wait_until="networkidle")
            skip_entrance_animation(page)
            wait_for_chat_input(page)
            input_val = page.locator("#message-input").input_value()
            results.append({"check": "T11 ?d=python", "ok": input_val.startswith("/python")})

            page.goto(BASE, wait_until="networkidle")
            results.append({
                "check": "T10 sidebar",
                "ok": page.locator("#conversation-sidebar").count() == 1,
            })

            # UI/UX roadmap: public-config carregado no boot
            iss_base = page.evaluate(
                """async () => {
                const r = await fetch('/api/public-config');
                if (!r.ok) return '';
                const j = await r.json();
                return j.iss_lesson_base || '';
            }"""
            )
            results.append({
                "check": "ISS config fetch in page",
                "ok": str(iss_base).startswith("http"),
            })
        finally:
            browser.close()

    print(json.dumps(results, indent=2, ensure_ascii=False))
    failed = [r for r in results if not r["ok"]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
