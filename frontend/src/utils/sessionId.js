import {
    clearConversation,
    loadConversation,
    saveConversation,
} from "./history.js";

const SID_PATTERN = /^[A-Za-z0-9_-]{8,128}$/;

/**
 * Identificador de sessão para contexto fixado no servidor (8–128 chars).
 * Persistido em `acl_conversation_v1` (localStorage).
 * @returns {string}
 */
export function getOrCreateSessionId() {
    try {
        const conv = loadConversation();
        if (conv.session_id && SID_PATTERN.test(conv.session_id)) {
            return conv.session_id;
        }
        const id = crypto.randomUUID().replace(/-/g, "");
        conv.session_id = id;
        saveConversation(conv);
        return id;
    } catch {
        return "localfallback";
    }
}

/** Novo session_id após «Nova conversa» / clear. */
export function regenerateSessionId() {
    try {
        const conv = loadConversation();
        const id = crypto.randomUUID().replace(/-/g, "");
        conv.session_id = id;
        saveConversation(conv);
        return id;
    } catch {
        return "localfallback";
    }
}

/** Limpa conversa e gera novo session_id. */
export function resetSessionStorage() {
    clearConversation();
    return regenerateSessionId();
}

