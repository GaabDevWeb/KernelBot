/**
 * Rótulo imediato para "Analisando resumos de …" (espelha prefixos do servidor; sem ACL_GLOBAL_CONTEXT).
 */

const DISCIPLINE_PREFIXES = [
    ["/planejamento-curso-carreira", "Planejamento de carreira"],
    ["/visualizacao-sql", "Visualização SQL"],
    ["/projeto-bloco", "Projeto bloco"],
    ["/python", "Python"],
];

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
    for (const [prefix, disc] of [
        ["/planejamento-curso-carreira", "planejamento"],
        ["/visualizacao-sql", "visualizacao-sql"],
        ["/projeto-bloco", "projeto-bloco"],
        ["/python", "python"],
    ]) {
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
