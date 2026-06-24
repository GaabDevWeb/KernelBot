#!/usr/bin/env node
/**
 * Validação rápida do frontend (substituto quando Puppeteer MCP indisponível).
 */
import { chromium } from "playwright";

const BASE = process.env.SMOKE_BASE_URL || "http://127.0.0.1:8001";

async function main() {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const results = [];

    try {
        await page.goto(BASE, { waitUntil: "networkidle", timeout: 30000 });

        // T5 hero copy
        const hero = await page.locator(".entrance-title-text").textContent({ timeout: 15000 }).catch(() => "");
        results.push({ check: "T5 hero", ok: /disciplinas/i.test(hero || "") });

        // T4 pills
        const pillCount = await page.locator(".entrance-discipline-pills .cmd-pill").count();
        results.push({ check: "T4 pills", ok: pillCount >= 5 });

        // T1 context notice hidden initially
        const noticeHidden = await page.locator("#context-window-notice").isHidden();
        results.push({ check: "T1 notice hidden empty", ok: noticeHidden });

        // T1 with 13 turns in storage
        await page.evaluate(() => {
            const turns = [];
            for (let i = 0; i < 13; i++) {
                turns.push({ role: "user", text: `q${i}`, ts: Date.now() });
                turns.push({ role: "bot", text: `a${i}`, ts: Date.now() });
            }
            localStorage.setItem(
                "kernel_conversations_v2",
                JSON.stringify({
                    activeId: "test",
                    conversations: [{ id: "test", title: "Test", createdAt: 0, updatedAt: 0, session_id: "x", turns }],
                }),
            );
        });
        await page.reload({ waitUntil: "networkidle" });
        const noticeVisible = await page.locator("#context-window-notice").isVisible();
        results.push({ check: "T1 notice with 26 turns", ok: noticeVisible });

        // T11 deep link
        await page.goto(`${BASE}/?d=python`, { waitUntil: "networkidle" });
        const inputVal = await page.locator("#message-input").inputValue();
        results.push({ check: "T11 ?d=python", ok: inputVal.startsWith("/python") });

        // T3 slash menu
        await page.goto(BASE, { waitUntil: "networkidle" });
        await page.locator("#message-input").fill("/py");
        await page.waitForTimeout(300);
        const menuVisible = await page.locator("#slash-command-menu:not([hidden])").isVisible();
        results.push({ check: "T3 slash menu", ok: menuVisible });

        // T10 sidebar
        const sidebar = await page.locator("#conversation-sidebar").count();
        results.push({ check: "T10 sidebar", ok: sidebar === 1 });

        console.log(JSON.stringify(results, null, 2));
        const failed = results.filter((r) => !r.ok);
        if (failed.length) process.exit(1);
    } finally {
        await browser.close();
    }
}

main().catch((e) => {
    console.error(e);
    process.exit(1);
});
