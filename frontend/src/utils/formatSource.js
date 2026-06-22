/**
 * Formata identificadores de fonte (db:discipline/slug) para exibição humana.
 * @param {string} raw
 * @returns {string}
 */
export function formatSourceLabel(raw) {
    const parts = parseSourceParts(raw);
    if (!parts) return "";
    if (parts.discipline && parts.lesson) {
        return `${parts.discipline} · ${parts.lesson}`;
    }
    return parts.lesson || parts.discipline || parts.raw;
}

/**
 * @param {string} raw
 * @returns {{ raw: string, discipline: string, lesson: string } | null}
 */
export function parseSourceParts(raw) {
    const s = String(raw || "").trim();
    if (!s) return null;

    if (s.startsWith("db:")) {
        const path = s.slice(3);
        const parts = path.split("/").filter(Boolean);
        if (parts.length >= 2) {
            return {
                raw: s,
                discipline: humanizeSegment(parts[0]),
                lesson: humanizeSlug(parts.slice(1).join("/")),
            };
        }
        if (parts.length === 1) {
            return { raw: s, discipline: "", lesson: humanizeSlug(parts[0]) };
        }
    }

    const segments = s.replace(/\\/g, "/").split("/").filter(Boolean);
    if (segments.length >= 2) {
        return {
            raw: s,
            discipline: humanizeSegment(segments[segments.length - 2]),
            lesson: humanizeSlug(segments[segments.length - 1]),
        };
    }
    return { raw: s, discipline: "", lesson: humanizeSlug(s) };
}

/**
 * @param {string} segment
 * @returns {string}
 */
function humanizeSegment(segment) {
    const map = {
        python: "Python",
        doc: "Documentação",
        _staging: "Staging",
        legacy: "Legado",
        fluencia: "Fluência IA",
        "fluencia-ia": "Fluência em IA",
        "python-processamento-dados": "Python — PPD",
        "sql-modelagem-relacional": "SQL — modelagem",
        "visualizacao-sql": "Visualização SQL",
        "planejamento-curso-carreira": "Planejamento de carreira",
        "projeto-bloco": "Projeto bloco",
    };
    const key = segment.toLowerCase();
    if (map[key]) return map[key];
    return segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, " ");
}

/**
 * @param {string} slug
 * @returns {string}
 */
function humanizeSlug(slug) {
    const base = slug.replace(/\.(json|md|txt)$/i, "");
    const withoutPrefix = base.replace(/^[^_]+__\d+__/, "");
    const text = (withoutPrefix || base).replace(/[-_]+/g, " ").trim();
    if (!text) return slug;
    return text.charAt(0).toUpperCase() + text.slice(1);
}
