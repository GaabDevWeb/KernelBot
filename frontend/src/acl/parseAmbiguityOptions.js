/**
 * Extrai e remove `<ambiguity_options>` / JSON `disambiguation_options` do texto streamed.
 */

import { processAmbiguityStreamDisplay } from "./ambiguityStreamBuffer.js";

const XML_BLOCK_RE = /<ambiguity_options\b[^>]*>[\s\S]*?<\/ambiguity_options>/gi;
const JSON_BLOCK_RE = /\{\s*"disambiguation_options"\s*:\s*\[[\s\S]*?\}\s*\}/gi;
const INCOMPLETE_TAG_RE = /<ambiguity_options\b[^>]*>[\s\S]*$/i;
const PARTIAL_OPEN_RE = /<(?:\/?ambiguity(?:_options)?)?$/i;

/**
 * @param {string} text
 * @returns {Array<{ title: string, discipline: string, slug: string }>}
 */
export function parseAmbiguityOptionsFromText(text) {
    const out = [];
    if (!text) return out;

    const xmlRe = new RegExp(XML_BLOCK_RE.source, "gi");
    let block;
    while ((block = xmlRe.exec(text)) !== null) {
        const inner = block[0];
        const optionRe = /<option\b([^>]*)\/?>/gi;
        let m;
        while ((m = optionRe.exec(inner)) !== null) {
            const attrs = m[1];
            const discipline = attrValue(attrs, "discipline");
            const slug = attrValue(attrs, "slug");
            const label = attrValue(attrs, "label") || attrValue(attrs, "title");
            if (label || slug) {
                out.push({
                    title: label || slug,
                    discipline,
                    slug,
                });
            }
        }
    }
    if (out.length) return out;

    const jsonRe = new RegExp(JSON_BLOCK_RE.source, "gi");
    while ((block = jsonRe.exec(text)) !== null) {
        try {
            const payload = JSON.parse(block[0]);
            const options = payload?.disambiguation_options;
            if (!Array.isArray(options)) continue;
            for (const raw of options) {
                if (!raw || typeof raw !== "object") continue;
                const discipline = String(raw.discipline || "").trim();
                const slug = String(raw.slug || "").trim();
                const label = String(raw.label || raw.title || "").trim();
                if (label || slug) {
                    out.push({ title: label || slug, discipline, slug });
                }
            }
        } catch {
            /* ignore malformed JSON */
        }
    }
    return out;
}

/**
 * @param {string} attrs
 * @param {string} name
 * @returns {string}
 */
function attrValue(attrs, name) {
    const re = new RegExp(`${name}\\s*=\\s*("([^"]*)"|'([^']*)')`, "i");
    const m = attrs.match(re);
    if (!m) return "";
    return (m[2] ?? m[3] ?? "").trim();
}

/**
 * @param {string} text
 * @returns {{ displayText: string, options: Array<{ title: string, discipline: string, slug: string }> }}
 */
export function stripAmbiguityMarkupFromText(text) {
    return processAmbiguityStreamDisplay(text);
}

/**
 * @param {Record<string, unknown> | null | undefined} meta
 * @returns {Array<{ title: string, discipline: string, slug: string }>}
 */
export function disambiguationOptionsFromMeta(meta) {
    const direct = meta?.disambiguation_options;
    if (Array.isArray(direct) && direct.length) {
        return direct.map((raw) => ({
            title: String(raw?.title || raw?.label || raw?.slug || "Aula").trim(),
            discipline: String(raw?.discipline || "").trim(),
            slug: String(raw?.slug || "").trim(),
        }));
    }
    const payload = meta?.payload;
    if (payload && typeof payload === "object" && Array.isArray(payload.suggested_candidates)) {
        return payload.suggested_candidates.map((raw) => ({
            title: String(raw?.title || raw?.slug || "Aula").trim(),
            discipline: String(raw?.discipline || "").trim(),
            slug: String(raw?.slug || "").trim(),
        }));
    }
    return [];
}
