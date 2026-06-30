/** Labels PT-BR para reason e grounding_policy no meta ACL. */

const REASON_LABELS = {
    ok: "",
    insufficient_context: "Pouco material nas aulas",
    ambiguous_retrieval: "Várias aulas parecidas",
    context_misaligned: "Trechos pouco relacionados",
    underspecified_query: "Pergunta vaga",
    low_confidence: "Confiança baixa",
    vague_but_high_risk: "Pergunta ampla",
    index_gap: "Aula fora do índice",
    provider_error: "Erro do provedor",
    post_generation_misalignment: "Revisão automática",
};

const GROUNDING_LABELS = {
    strict: "Modo conservador",
    anchored: "Modo didático",
    hybrid: "Modo misto",
};

/**
 * @param {string} reason
 * @returns {string} Label curto ou vazio se ok
 */
export function reasonLabel(reason) {
    const key = String(reason || "").trim();
    if (!key || key === "ok") return "";
    return REASON_LABELS[key] || key.replace(/_/g, " ");
}

/**
 * @param {string} policy
 * @returns {string}
 */
export function groundingPolicyLabel(policy) {
    const key = String(policy || "").trim().toLowerCase();
    if (!key || key === "strict") return "";
    return GROUNDING_LABELS[key] || key;
}
