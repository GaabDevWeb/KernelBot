import { stripLeadingDisciplineCommand } from "../scopeMenu.js";

export const CONVERSATIONS_STORE_KEY = "kernel_conversations_v2";
export const LEGACY_CONVERSATION_KEY = "acl_conversation_v1";

/**
 * @typedef {import('../utils/history.js').ConversationTurn} ConversationTurn
 * @typedef {{ id: string, title: string, createdAt: number, updatedAt: number, session_id: string | null, turns: ConversationTurn[] }} StoredConversation
 */

/**
 * @returns {{ activeId: string | null, conversations: StoredConversation[] }}
 */
function emptyStore() {
    return { activeId: null, conversations: [] };
}

let migrated = false;

function newId() {
    return crypto.randomUUID().replace(/-/g, "");
}

/**
 * @param {string} text
 */
export function titleFromFirstMessage(text) {
    let t = stripLeadingDisciplineCommand(String(text || "").trim());
    t = t.replace(/^\/(?:doc|content|reset|limpar)\b\s*/i, "").trim();
    if (!t) t = "Nova conversa";
    if (t.length > 48) t = `${t.slice(0, 45)}…`;
    return t;
}

function migrateLegacyIfNeeded() {
    if (migrated) return;
    migrated = true;
    try {
        if (localStorage.getItem(CONVERSATIONS_STORE_KEY)) return;
        const raw = localStorage.getItem(LEGACY_CONVERSATION_KEY);
        if (!raw) return;
        const parsed = JSON.parse(raw);
        const turns = Array.isArray(parsed?.turns) ? parsed.turns : [];
        const firstUser = turns.find((t) => t?.role === "user");
        const id = newId();
        const conv = {
            id,
            title: firstUser?.text ? titleFromFirstMessage(firstUser.text) : "Conversa anterior",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            session_id: typeof parsed?.session_id === "string" ? parsed.session_id : null,
            turns,
        };
        localStorage.setItem(
            CONVERSATIONS_STORE_KEY,
            JSON.stringify({ activeId: id, conversations: [conv] }),
        );
    } catch {
        /* ignora */
    }
}

/**
 * @returns {{ activeId: string | null, conversations: StoredConversation[] }}
 */
export function loadStore() {
    migrateLegacyIfNeeded();
    try {
        const raw = localStorage.getItem(CONVERSATIONS_STORE_KEY);
        if (!raw) return emptyStore();
        const parsed = JSON.parse(raw);
        const conversations = Array.isArray(parsed?.conversations)
            ? parsed.conversations.filter((c) => c && c.id)
            : [];
        return {
            activeId: typeof parsed?.activeId === "string" ? parsed.activeId : null,
            conversations,
        };
    } catch {
        return emptyStore();
    }
}

/**
 * @param {{ activeId: string | null, conversations: StoredConversation[] }} store
 */
export function saveStore(store) {
    migrateLegacyIfNeeded();
    try {
        localStorage.setItem(CONVERSATIONS_STORE_KEY, JSON.stringify(store));
    } catch {
        /* quota */
    }
}

/**
 * @returns {StoredConversation}
 */
export function getActiveConversation() {
    const store = loadStore();
    if (store.activeId) {
        const found = store.conversations.find((c) => c.id === store.activeId);
        if (found) return found;
    }
    if (store.conversations.length) {
        return store.conversations[0];
    }
    return createConversation({ activate: true });
}

/**
 * @param {{ activate?: boolean, title?: string }} [opts]
 * @returns {StoredConversation}
 */
export function createConversation(opts = {}) {
    const store = loadStore();
    const conv = {
        id: newId(),
        title: opts.title || "Nova conversa",
        createdAt: Date.now(),
        updatedAt: Date.now(),
        session_id: null,
        turns: [],
    };
    store.conversations.unshift(conv);
    if (opts.activate !== false) store.activeId = conv.id;
    saveStore(store);
    return conv;
}

/**
 * @param {string} id
 * @returns {StoredConversation | null}
 */
export function switchConversation(id) {
    const store = loadStore();
    const conv = store.conversations.find((c) => c.id === id);
    if (!conv) return null;
    store.activeId = id;
    saveStore(store);
    return conv;
}

/**
 * @param {{ session_id?: string | null, turns: ConversationTurn[], title?: string }} data
 */
export function updateActiveConversation(data) {
    const store = loadStore();
    let conv = store.conversations.find((c) => c.id === store.activeId);
    if (!conv) {
        conv = createConversation({ activate: true });
        store.activeId = conv.id;
        conv = store.conversations.find((c) => c.id === conv.id) || conv;
    }
    conv.turns = data.turns;
    conv.session_id = data.session_id ?? conv.session_id;
    conv.updatedAt = Date.now();
    if (data.title) conv.title = data.title;
    else {
        const firstUser = conv.turns.find((t) => t.role === "user");
        if (firstUser && (conv.title === "Nova conversa" || !conv.title)) {
            conv.title = titleFromFirstMessage(firstUser.text);
        }
    }
    saveStore(store);
}

export function listConversations() {
    return loadStore().conversations.sort((a, b) => b.updatedAt - a.updatedAt);
}

export function clearAllConversations() {
    try {
        localStorage.removeItem(CONVERSATIONS_STORE_KEY);
        localStorage.removeItem(LEGACY_CONVERSATION_KEY);
    } catch {
        /* ignora */
    }
    migrated = true;
}
