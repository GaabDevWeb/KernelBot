/** Progresso inferido por disciplina — localStorage kernel_progress_v1 */

export const PROGRESS_STORE_KEY = "kernel_progress_v1";

/**
 * @returns {Record<string, string[]>}
 */
function loadStore() {
    try {
        const raw = localStorage.getItem(PROGRESS_STORE_KEY);
        if (!raw) return {};
        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== "object") return {};
        /** @type {Record<string, string[]>} */
        const out = {};
        for (const [disc, slugs] of Object.entries(parsed)) {
            if (Array.isArray(slugs)) {
                out[disc] = slugs.filter((s) => typeof s === "string" && s);
            }
        }
        return out;
    } catch {
        return {};
    }
}

/**
 * @param {Record<string, string[]>} store
 */
function saveStore(store) {
    localStorage.setItem(PROGRESS_STORE_KEY, JSON.stringify(store));
}

/**
 * @param {string} discipline
 * @param {string} slug
 */
export function markVisited(discipline, slug) {
    const disc = String(discipline || "").trim().toLowerCase();
    const s = String(slug || "").trim().toLowerCase();
    if (!disc || !s) return;
    const store = loadStore();
    const set = new Set(store[disc] || []);
    if (set.has(s)) return;
    set.add(s);
    store[disc] = [...set];
    saveStore(store);
}

/**
 * @param {string} discipline
 * @returns {Set<string>}
 */
export function getProgress(discipline) {
    const disc = String(discipline || "").trim().toLowerCase();
    return new Set(loadStore()[disc] || []);
}

/**
 * @param {Array<{ slug: string, order?: number, title?: string }>} lessons
 * @param {Set<string>} visited
 * @returns {{ slug: string, title?: string } | null}
 */
export function suggestNext(lessons, visited) {
    const sorted = [...lessons].sort((a, b) => {
        const oa = typeof a.order === "number" ? a.order : 9999;
        const ob = typeof b.order === "number" ? b.order : 9999;
        if (oa !== ob) return oa - ob;
        return String(a.title || a.slug).localeCompare(String(b.title || b.slug), "pt-BR");
    });
    for (const lesson of sorted) {
        const slug = String(lesson.slug || "").toLowerCase();
        if (slug && !visited.has(slug)) {
            return { slug: lesson.slug, title: lesson.title };
        }
    }
    return null;
}

/**
 * @param {{ sourceDetails?: Array<Record<string, unknown>>, turnMeta?: { aclSnapshot?: Record<string, unknown> } }} turn
 * @param {Record<string, unknown> | null} [lastMeta]
 */
export function markVisitedFromTurn(turn, _lastMeta) {
    const details = turn.sourceDetails;
    if (Array.isArray(details)) {
        for (const d of details) {
            const disc = String(d.discipline || "").trim().toLowerCase();
            const slug = String(d.slug || "").trim().toLowerCase();
            if (disc && slug) markVisited(disc, slug);
        }
    }
}

/**
 * Varre histórico e reconstrói progresso a partir de source_details.
 * @param {Array<{ role?: string, sourceDetails?: Array<Record<string, unknown>> }>} turns
 */
export function rebuildProgressFromHistory(turns) {
    if (!Array.isArray(turns)) return;
    for (const turn of turns) {
        if (turn.role !== "bot") continue;
        markVisitedFromTurn(turn);
    }
}
