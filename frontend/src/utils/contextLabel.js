/**
 * Rótulo imediato para "Analisando resumos de …" (SSOT: config/disciplines.json).
 */

import {
    DISCIPLINE_PREFIXES,
    DISCIPLINE_SILO_BY_COMMAND,
} from "../config/disciplines.js";

/**
 * @param {string} raw
 * @returns {string}
 */
export function immediateContextLabel(raw) {
    const text = (raw || "").trimStart();

    if (text.startsWith("/doc")) {
        return "Documentação (doc)";
    }
    if (text.startsWith("/content")) {
        return "Base geral";
    }

    for (const [prefix, label] of DISCIPLINE_PREFIXES) {
        if (!text.startsWith(prefix)) continue;
        const tail = text.slice(prefix.length);
        if (tail.length > 0 && !tail[0].match(/\s/)) continue;
        return label;
    }

    return "Assistente geral";
}

/**
 * Identificador CSS para estado do silo no input (null = nenhum).
 * @param {string} raw
 * @returns {string | null}
 */
export function siloClassSuffix(raw) {
    const text = (raw || "").trimStart();
    if (text.startsWith("/doc")) return "doc";
    if (text.startsWith("/content")) return "content";
    for (const [prefix, disc] of Object.entries(DISCIPLINE_SILO_BY_COMMAND)) {
        if (!text.startsWith(prefix)) continue;
        const tail = text.slice(prefix.length);
        if (tail.length > 0 && !tail[0].match(/\s/)) continue;
        return disc;
    }
    return null;
}

/**
 * @param {string} raw
 * @returns {string | null}
 */
export function siloDisplayName(raw) {
    const text = (raw || "").trimStart();
    if (text.startsWith("/doc")) return "Documentação (doc)";
    if (text.startsWith("/content")) return "/content (RAG global)";
    for (const [prefix, label] of DISCIPLINE_PREFIXES) {
        if (!text.startsWith(prefix)) continue;
        const tail = text.slice(prefix.length);
        if (tail.length > 0 && !tail[0].match(/\s/)) continue;
        return label;
    }
    return null;
}

/**
 * Comando e rótulo da disciplina activa no input (null se busca geral).
 * @param {string} raw
 * @returns {{ command: string, label: string } | null}
 */
export function activeDisciplineFromInput(raw) {
    const text = (raw || "").trimStart();
    if (text.startsWith("/doc")) {
        return { command: "/doc", label: "Documentação (doc)" };
    }
    if (text.startsWith("/content")) {
        return { command: "/content", label: "Base geral" };
    }
    for (const [prefix, label] of DISCIPLINE_PREFIXES) {
        if (!text.startsWith(prefix)) continue;
        const tail = text.slice(prefix.length);
        if (tail.length > 0 && !tail[0].match(/\s/)) continue;
        return { command: prefix, label };
    }
    return null;
}

/**
 * Comando e rótulo da disciplina activa no input (null se busca geral).
 * @param {string} raw
 * @returns {{ command: string, label: string } | null}
 */
export function activeDisciplineFromInput(raw) {
    const text = (raw || "").trimStart();
    if (text.startsWith("/doc")) {
        return { command: "/doc", label: "Documentação (doc)" };
    }
    if (text.startsWith("/content")) {
        return { command: "/content", label: "Base geral" };
    }
    for (const [prefix, label] of DISCIPLINE_PREFIXES) {
        if (!text.startsWith(prefix)) continue;
        const tail = text.slice(prefix.length);
        if (tail.length > 0 && !tail[0].match(/\s/)) continue;
        return { command: prefix, label };
    }
    return null;
}
