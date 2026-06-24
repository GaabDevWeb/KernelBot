/** @typedef {{ role: 'user' | 'bot', text: string, sources?: string[], sourceDetails?: Array<Record<string, unknown>>, turnMeta?: import('../chat/restoreTurn.js').TurnMeta, ts?: number }} ConversationTurn */

import {
    clearAllConversations,
    getActiveConversation,
    updateActiveConversation,
} from "./conversations.js";

export const CONVERSATION_KEY = "acl_conversation_v1";
export const LEGACY_SESSION_KEY = "acl_session_id";
export const LEGACY_HISTORY_KEY = "acl_history";

export const MAX_TURNS = 30;
export const MAX_CHARS = 200_000;
/** Máximo enviado ao servidor por turno (servidor re-trunca). */
export const MAX_API_MESSAGES = 12;

/**
 * Verifica se o histórico excede a janela enviada ao modelo.
 * @param {number} [turnCount] — se omitido, usa turnos persistidos
 */
export function exceedsApiWindow(turnCount) {
    const count =
        typeof turnCount === "number"
            ? turnCount
            : loadConversation().turns.length;
    return count > MAX_API_MESSAGES;
}

/** @returns {{ session_id: string | null, turns: ConversationTurn[] }} */
function emptyConversation() {
    return { session_id: null, turns: [] };
}

/**
 * @returns {{ session_id: string | null, turns: ConversationTurn[] }}
 */
export function loadConversation() {
    const conv = getActiveConversation();
    return {
        session_id: conv.session_id ?? null,
        turns: Array.isArray(conv.turns) ? conv.turns : [],
    };
}

/**
 * @param {{ session_id?: string | null, turns: ConversationTurn[] }} conv
 */
export function saveConversation(conv) {
    let turns = [...(conv.turns || [])];
    let totalChars = turns.reduce((n, t) => n + (t.text?.length || 0), 0);
    while (turns.length > MAX_TURNS || totalChars > MAX_CHARS) {
        const removed = turns.shift();
        if (!removed) break;
        totalChars -= removed.text?.length || 0;
    }
    updateActiveConversation({
        session_id: conv.session_id ?? null,
        turns,
    });
}

export function clearConversation() {
    clearAllConversations();
}

/** Compatibilidade com ChatView — formato legado UI. */
export function loadHistory() {
    return loadConversation().turns.map(({ role, text, sources, sourceDetails, turnMeta }) => ({
        role,
        text,
        ...(sources?.length ? { sources } : {}),
        ...(sourceDetails?.length ? { sourceDetails } : {}),
        ...(turnMeta ? { turnMeta } : {}),
    }));
}

/**
 * @param {Array<{ role: string, text: string, sources?: string[], sourceDetails?: Array<Record<string, unknown>>, turnMeta?: import('../chat/restoreTurn.js').TurnMeta }>} history
 */
export function saveHistory(history) {
    const conv = loadConversation();
    conv.turns = history.map((h) => ({
        role: h.role === "bot" ? "bot" : "user",
        text: String(h.text || ""),
        ...(Array.isArray(h.sources) && h.sources.length
            ? { sources: h.sources }
            : {}),
        ...(Array.isArray(h.sourceDetails) && h.sourceDetails.length
            ? { sourceDetails: h.sourceDetails }
            : {}),
        ...(h.turnMeta && typeof h.turnMeta === "object" ? { turnMeta: h.turnMeta } : {}),
        ts: Date.now(),
    }));
    saveConversation(conv);
}

/**
 * Turnos anteriores para POST /chat (exclui a mensagem do turno corrente).
 * @returns {Array<{ role: 'user' | 'assistant', content: string }>}
 */
export function getHistoryForApi() {
    const turns = loadConversation().turns;
    const out = [];
    for (const t of turns) {
        if (t.role === "user") {
            out.push({ role: "user", content: t.text });
        } else if (t.role === "bot") {
            out.push({ role: "assistant", content: t.text });
        }
    }
    return out.slice(-MAX_API_MESSAGES);
}

/**
 * @param {string | null} sessionId
 */
export function persistSessionId(sessionId) {
    const conv = loadConversation();
    conv.session_id = sessionId;
    saveConversation(conv);
}

export function getPersistedSessionId() {
    return loadConversation().session_id;
}

export { emptyConversation };
