/** @typedef {{ role: 'user' | 'bot', text: string, sources?: string[], ts?: number }} ConversationTurn */

export const CONVERSATION_KEY = "acl_conversation_v1";
export const LEGACY_SESSION_KEY = "acl_session_id";
export const LEGACY_HISTORY_KEY = "acl_history";

export const MAX_TURNS = 30;
export const MAX_CHARS = 200_000;
/** Máximo enviado ao servidor por turno (servidor re-trunca). */
export const MAX_API_MESSAGES = 12;

/** @returns {{ session_id: string | null, turns: ConversationTurn[] }} */
function emptyConversation() {
    return { session_id: null, turns: [] };
}

let legacyMigrated = false;

function migrateLegacyStorage() {
    if (legacyMigrated) return;
    legacyMigrated = true;
    try {
        if (localStorage.getItem(CONVERSATION_KEY)) return;
        const legacyHist = sessionStorage.getItem(LEGACY_HISTORY_KEY);
        const legacySid = sessionStorage.getItem(LEGACY_SESSION_KEY);
        if (!legacyHist && !legacySid) return;
        /** @type {ConversationTurn[]} */
        let turns = [];
        if (legacyHist) {
            const parsed = JSON.parse(legacyHist);
            if (Array.isArray(parsed)) {
                turns = parsed
                    .filter((t) => t && (t.role === "user" || t.role === "bot") && t.text)
                    .map((t) => ({
                        role: t.role,
                        text: String(t.text),
                        ...(Array.isArray(t.sources) ? { sources: t.sources } : {}),
                        ts: Date.now(),
                    }));
            }
        }
        saveConversation({
            session_id: typeof legacySid === "string" ? legacySid : null,
            turns,
        });
        sessionStorage.removeItem(LEGACY_HISTORY_KEY);
        sessionStorage.removeItem(LEGACY_SESSION_KEY);
    } catch {
        /* ignora migração corrompida */
    }
}

/**
 * @returns {{ session_id: string | null, turns: ConversationTurn[] }}
 */
export function loadConversation() {
    migrateLegacyStorage();
    try {
        const raw = localStorage.getItem(CONVERSATION_KEY);
        if (!raw) return emptyConversation();
        const parsed = JSON.parse(raw);
        const turns = Array.isArray(parsed?.turns)
            ? parsed.turns.filter(
                  (t) =>
                      t &&
                      (t.role === "user" || t.role === "bot") &&
                      typeof t.text === "string",
              )
            : [];
        return {
            session_id:
                typeof parsed?.session_id === "string" ? parsed.session_id : null,
            turns,
        };
    } catch {
        return emptyConversation();
    }
}

/**
 * @param {{ session_id?: string | null, turns: ConversationTurn[] }} conv
 */
export function saveConversation(conv) {
    migrateLegacyStorage();
    let turns = [...(conv.turns || [])];
    let totalChars = turns.reduce((n, t) => n + (t.text?.length || 0), 0);
    while (turns.length > MAX_TURNS || totalChars > MAX_CHARS) {
        const removed = turns.shift();
        if (!removed) break;
        totalChars -= removed.text?.length || 0;
    }
    try {
        localStorage.setItem(
            CONVERSATION_KEY,
            JSON.stringify({
                session_id: conv.session_id ?? null,
                turns,
            }),
        );
    } catch {
        /* quota exceeded */
    }
}

export function clearConversation() {
    try {
        localStorage.removeItem(CONVERSATION_KEY);
    } catch {
        /* ignora */
    }
    legacyMigrated = true;
    try {
        sessionStorage.removeItem(LEGACY_HISTORY_KEY);
        sessionStorage.removeItem(LEGACY_SESSION_KEY);
    } catch {
        /* ignora */
    }
}

/** Compatibilidade com ChatView — formato legado UI. */
export function loadHistory() {
    return loadConversation().turns.map(({ role, text, sources }) => ({
        role,
        text,
        ...(sources?.length ? { sources } : {}),
    }));
}

/**
 * @param {Array<{ role: string, text: string, sources?: string[] }>} history
 */
export function saveHistory(history) {
    const conv = loadConversation();
    conv.turns = history.map((h) => ({
        role: h.role === "bot" ? "bot" : "user",
        text: String(h.text || ""),
        ...(Array.isArray(h.sources) && h.sources.length
            ? { sources: h.sources }
            : {}),
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
