/**
 * Filtra markup de desambiguação no stream SSE: oculta tags parciais,
 * separa texto antes / depois do bloco XML e faz flush em stream cortado.
 */

import { parseAmbiguityOptionsFromText } from "./parseAmbiguityOptions.js";

const OPEN = "<ambiguity_options";
const CLOSE = "</ambiguity_options>";
/** Legado: opções ainda incompletas (sem `/>` nem `</option>`). */
const OPTION_RE = /<option\b([^>]*)\/?>/gi;
/** Opção completa: auto-fechada `<option …/>`. */
const OPTION_SELF_CLOSE_RE = /<option\b([^>]*?)\s*\/>/gi;
/** Opção completa: par vazio `<option …></option>` (comum quando o LLM omite `/`). */
const OPTION_PAIR_CLOSE_RE = /<option\b([^>]*?)>\s*<\/option>/gi;

export const AMBIGUITY_STREAM_PLACEHOLDER =
    "A preparar opções de escolha com base no material indexado…";

export const STREAM_TRUNCATED_AMBIGUITY_MSG =
    "A resposta foi interrompida antes de concluir as opções. Reformule a pergunta ou tente novamente.";

export function optionAttrsWellFormed(attrs) {
    if (!attrs || attrs.includes("<")) return false;
    if (/=\s*"[^"]*$/.test(attrs) || /=\s*'[^']*$/.test(attrs)) return false;
    return true;
}

function attrValue(attrs, name) {
    const re = new RegExp(`${name}\\s*=\\s*("([^"]*)"|'([^']*)')`, "i");
    const m = attrs.match(re);
    if (!m) return "";
    return (m[2] ?? m[3] ?? "").trim();
}

function optionFromAttrs(attrs) {
    if (!optionAttrsWellFormed(attrs)) return null;
    const discipline = attrValue(attrs, "discipline");
    const slug = attrValue(attrs, "slug");
    const label = attrValue(attrs, "label") || attrValue(attrs, "title");
    if (!label && !slug) return null;
    return { title: label || slug, discipline, slug };
}

/**
 * Extrai opções com fecho sintático completo dentro de um fragmento XML.
 * Aceita `<option …/>` e `<option …></option>`; ignora tags abertas sem fecho.
 * @param {string} fragment
 * @returns {Array<{ title: string, discipline: string, slug: string }>}
 */
export function parseCompleteOptionsFromFragment(fragment) {
    if (!fragment) return [];
    const out = [];
    const seenKeys = new Set();
    const seenStarts = new Set();

    for (const re of [OPTION_SELF_CLOSE_RE, OPTION_PAIR_CLOSE_RE]) {
        const pattern = new RegExp(re.source, re.flags);
        let m;
        while ((m = pattern.exec(fragment)) !== null) {
            if (seenStarts.has(m.index)) continue;
            seenStarts.add(m.index);
            const item = optionFromAttrs(m[1]);
            if (!item) continue;
            const key = `${item.discipline}:${item.slug}:${item.title}`;
            if (seenKeys.has(key)) continue;
            seenKeys.add(key);
            out.push(item);
        }
    }
    return out;
}

/**
 * Opções com tag completa (imutáveis durante o stream).
 * @param {string} fullText
 * @returns {Array<{ title: string, discipline: string, slug: string }>}
 */
export function parseCompleteOptionsIncremental(fullText) {
    if (!fullText) return [];
    const lower = fullText.toLowerCase();
    const openIdx = lower.indexOf(OPEN);
    if (openIdx === -1) return [];

    const closeIdx = lower.indexOf(CLOSE, openIdx);
    const end = closeIdx === -1 ? fullText.length : closeIdx + CLOSE.length;
    const fragment = fullText.slice(openIdx, end);
    return parseCompleteOptionsFromFragment(fragment);
}

export function parseOptionsFromOpenFragment(text, openIdx) {
    const fragment = text.slice(openIdx);
    const complete = parseCompleteOptionsFromFragment(fragment);
    if (complete.length) return complete;
    const out = [];
    const re = new RegExp(OPTION_RE.source, "gi");
    let m;
    while ((m = re.exec(fragment)) !== null) {
        const item = optionFromAttrs(m[1]);
        if (item) out.push(item);
    }
    return out;
}

export function stripPartialAmbiguityTagSuffix(text) {
    const idx = text.lastIndexOf("<");
    if (idx === -1) return text;
    const cand = text.slice(idx).toLowerCase();
    if (OPEN.startsWith(cand) || CLOSE.startsWith(cand)) {
        return text.slice(0, idx);
    }
    return text;
}

function normalizeProse(text) {
    return text.replace(/\n{3,}/g, "\n\n").trim();
}

/**
 * Percorre o texto e separa prosa antes do bloco, depois do fecho, e estado do bloco.
 * @param {string} fullText
 */
export function processAmbiguityStreamDisplay(fullText) {
    const empty = {
        proseBefore: "",
        proseAfter: "",
        displayText: "",
        options: [],
        insideOpenBlock: false,
        blockClosed: false,
    };
    if (!fullText) return empty;

    let proseBefore = "";
    let proseAfter = "";
    let cursor = 0;
    let insideOpenBlock = false;
    let blockClosed = false;
    const lower = fullText.toLowerCase();

    while (cursor < fullText.length) {
        const openIdx = lower.indexOf(OPEN, cursor);
        if (openIdx === -1) {
            const tail = stripPartialAmbiguityTagSuffix(fullText.slice(cursor));
            if (blockClosed) proseAfter += tail;
            else proseBefore += tail;
            break;
        }

        const segment = fullText.slice(cursor, openIdx);
        if (blockClosed) proseAfter += segment;
        else proseBefore += segment;

        const closeIdx = lower.indexOf(CLOSE, openIdx);
        if (closeIdx === -1) {
            insideOpenBlock = true;
            break;
        }

        blockClosed = true;
        insideOpenBlock = false;
        cursor = closeIdx + CLOSE.length;
    }

    const options = parseAmbiguityOptionsFromText(fullText);
    const before = normalizeProse(proseBefore);
    const after = normalizeProse(proseAfter);
    const displayText = after ? (before ? `${before}\n\n${after}` : after) : before;

    return {
        proseBefore: before,
        proseAfter: after,
        displayText,
        options,
        insideOpenBlock,
        blockClosed,
    };
}

export function finalizeAmbiguityStreamDisplay(fullText) {
    const live = processAmbiguityStreamDisplay(fullText);

    if (live.blockClosed && live.options.length > 0) {
        return { ...live, streamTruncated: false };
    }

    const lower = (fullText || "").toLowerCase();
    const openIdx = lower.indexOf(OPEN);
    if (openIdx === -1) {
        return { ...live, streamTruncated: false };
    }

    const closeIdx = lower.indexOf(CLOSE, openIdx);
    if (closeIdx !== -1) {
        const options = parseAmbiguityOptionsFromText(fullText);
        return {
            ...live,
            options: options.length ? options : live.options,
            insideOpenBlock: false,
            blockClosed: true,
            streamTruncated: false,
        };
    }

    const partialOptions = parseOptionsFromOpenFragment(fullText, openIdx);
    const before = normalizeProse(
        stripPartialAmbiguityTagSuffix(fullText.slice(0, openIdx)),
    );

    return {
        proseBefore: before,
        proseAfter: "",
        displayText: before,
        options: partialOptions,
        insideOpenBlock: true,
        blockClosed: false,
        streamTruncated: partialOptions.length === 0,
    };
}

/**
 * Opções finais: meta do backend (pós-stream) tem prioridade; depois parse do texto.
 * @param {Array<{ title: string, discipline: string, slug: string }>} metaOptions
 * @param {Array<{ title: string, discipline: string, slug: string }>} parsedOptions
 */
export function mergeDisambiguationOptions(metaOptions, parsedOptions) {
    const seen = new Set();
    const out = [];
    for (const list of [metaOptions, parsedOptions]) {
        for (const raw of list) {
            const key = `${raw.discipline || ""}:${raw.slug || ""}:${raw.title || ""}`;
            if (seen.has(key)) continue;
            seen.add(key);
            if (raw.title || raw.slug) out.push(raw);
        }
    }
    return out;
}
