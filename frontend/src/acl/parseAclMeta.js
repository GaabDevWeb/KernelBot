/** Razões de hard_stop que usam UI estruturada (sem markdown streaming). */
export const STRUCTURED_HARD_STOP_REASONS = ["index_gap", "ambiguous_retrieval"];

/**
 * Geração permitida neste turno (contrato ACL_META v=3).
 * Fallback legado: `decision === "answer"` quando `allow_generation` ausente.
 * @param {Record<string, unknown> | null | undefined} meta
 * @returns {boolean}
 */
export function allowsGeneration(meta) {
    if (meta && typeof meta.allow_generation === "boolean") {
        return meta.allow_generation;
    }
    if (meta?.decision === "answer") return true;
    if (meta?.decision === "hard_stop") return false;
    return true;
}

/**
 * Desambiguação com LLM (`ACL_DISAMBIGUATION_ENABLED`) — stream markdown, sem chips.
 * @param {Record<string, unknown> | null | undefined} meta
 * @returns {boolean}
 */
export function isDisambiguationGeneration(meta) {
    return allowsGeneration(meta) && String(meta?.reason || "") === "ambiguous_retrieval";
}

/** Mapa discipline → prefixo de comando (espelha `engine/context.py`). */
const DISCIPLINE_TO_COMMAND = {
    python: "/python",
    "visualizacao-sql": "/visualizacao-sql",
    "projeto-bloco": "/projeto-bloco",
    "planejamento-curso-carreira": "/planejamento-curso-carreira",
};

/**
 * @param {string | undefined} discipline
 * @returns {string} ex.: `/python `
 */
export function scopePrefixForDiscipline(discipline) {
    const key = (discipline || "").trim().toLowerCase();
    const cmd = DISCIPLINE_TO_COMMAND[key];
    return cmd ? `${cmd} ` : "";
}

/**
 * Mensagem de follow-up após escolha de candidato (desambiguação).
 * @param {{ discipline?: string, slug?: string, title?: string }} candidate
 * @returns {string}
 */
export function buildDisambiguationFollowUp(candidate) {
    const prefix = scopePrefixForDiscipline(candidate?.discipline);
    const slug = (candidate?.slug || "").trim();
    if (prefix && slug) {
        return `${prefix}Conteúdo da aula ${slug}: `;
    }
    const title = (candidate?.title || slug || "aula").trim();
    return `Conteúdo da aula ${title}: `;
}

/**
 * Normaliza payload de hard_stop (espelha `_normalize_hard_stop_payload` no backend).
 * @param {string} reason
 * @param {Record<string, unknown> | null | undefined} payload
 * @returns {Record<string, unknown> | null}
 */
export function normalizeHardStopPayload(reason, payload) {
    if (!payload || typeof payload !== "object") return null;
    const out = { ...payload };
    if (reason === "index_gap") {
        out.suggested_candidates = Array.isArray(out.suggested_candidates)
            ? out.suggested_candidates
            : [];
    } else if (reason === "ambiguous_retrieval") {
        out.expected_lesson = null;
        out.suggested_candidates = Array.isArray(out.suggested_candidates)
            ? [...out.suggested_candidates]
            : [];
    }
    return out;
}

/**
 * @param {Record<string, unknown> | null | undefined} meta
 * @returns {boolean}
 */
export function isStructuredHardStop(meta) {
    if (allowsGeneration(meta)) return false;
    return STRUCTURED_HARD_STOP_REASONS.includes(String(meta?.reason || ""));
}

/**
 * @param {string} reason
 * @param {Record<string, unknown> | null} payload
 * @returns {boolean}
 */
export function shouldMountIndexGap(reason, payload, meta) {
    return (
        !allowsGeneration(meta) &&
        reason === "index_gap" &&
        payload?.expected_lesson != null
    );
}

/**
 * @param {string} reason
 * @param {Record<string, unknown> | null} payload
 * @returns {boolean}
 */
export function shouldMountDisambiguationChips(reason, payload, meta) {
    const candidates = payload?.suggested_candidates;
    const hasCandidates = Array.isArray(candidates) && candidates.length > 0;
    if (!hasCandidates) return false;
    if (!allowsGeneration(meta) && reason === "ambiguous_retrieval") return true;
    return isDisambiguationGeneration(meta) && hasCandidates;
}

/**
 * Override pós-geração (Fase 3) — substitui badge/hint de sucesso.
 * @param {Record<string, unknown> | null | undefined} meta
 * @returns {boolean}
 */
export function isPostGenerationOverride(meta) {
    if (meta?.post_generation_override === true || meta?.misalignment === true) {
        return true;
    }
    return String(meta?.reason || "") === "post_generation_misalignment";
}

/**
 * Aviso pós-geração sem anular a resposta (anchored/hybrid).
 * @param {Record<string, unknown> | null | undefined} meta
 * @returns {boolean}
 */
export function isPostGenerationAdvisory(meta) {
    return (
        meta?.post_generation_advisory === true &&
        !isPostGenerationOverride(meta)
    );
}

/**
 * Hint de escopo/pin (meta.scope_hint).
 * @param {Record<string, unknown> | null | undefined} meta
 * @returns {string | null}
 */
export function scopeHintFromMeta(meta) {
    const h = meta?.scope_hint;
    if (typeof h !== "string") return null;
    const t = h.trim();
    return t.length ? t : null;
}

/**
 * Nota de rodapé quando pin + retrieval misturam fontes (meta.sources_note).
 * @param {Record<string, unknown> | null | undefined} meta
 * @returns {string | null}
 */
export function sourcesNoteFromMeta(meta) {
    const n = meta?.sources_note;
    if (typeof n !== "string") return null;
    const t = n.trim();
    return t.length ? t : null;
}

/**
 * Prioridade de badge no rodapé: misalignment → disambiguation → scope → advisory → none.
 * @param {Record<string, unknown> | null | undefined} meta
 * @returns {{ variant: "none" | "disambiguation" | "misalignment" | "advisory" | "scope", text: string | null }}
 */
export function resolveTurnHintVariant(meta) {
    if (isPostGenerationOverride(meta)) {
        return { variant: "misalignment", text: null };
    }
    if (isDisambiguationGeneration(meta)) {
        return { variant: "disambiguation", text: null };
    }
    const scopeText = scopeHintFromMeta(meta);
    if (scopeText) {
        return { variant: "scope", text: scopeText };
    }
    if (isPostGenerationAdvisory(meta)) {
        return { variant: "advisory", text: null };
    }
    return { variant: "none", text: null };
}
