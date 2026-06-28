import { getDisciplines } from "../config/disciplines.js";

export const CONVERSATIONS_STORE_KEY = "kernel_conversations_v2";
export const LEGACY_CONVERSATION_KEY = "acl_conversation_v1";

/**
 * @typedef {import('../utils/history.js').ConversationTurn} ConversationTurn
 * @typedef {{ id: string, title: string, createdAt: number, updatedAt: number, session_id: string | null, disciplineId: string | null, turns: ConversationTurn[] }} StoredConversation
 */

/**
 * Remove prefixo de disciplina no início da mensagem (evita import circular com scopeMenu).
 * @param {string} text
 */
function stripLeadingDisciplineCommand(text) {
    const trimmed = (text || "").trimStart();
    const prefixes = getDisciplines()
        .map((d) => d.command)
        .sort((a, b) => b.length - a.length);
    for (const cmd of prefixes) {
        if (!trimmed.startsWith(cmd)) continue;
        const tail = trimmed.slice(cmd.length);
        if (tail.length > 0 && !tail[0].match(/\s/)) continue;
        return tail.trimStart();
    }
    if (trimmed.startsWith("/doc")) {
        const tail = trimmed.slice(4);
        if (!tail.length || tail[0].match(/\s/)) return tail.trimStart();
    }
    if (trimmed.startsWith("/content")) {
        const tail = trimmed.slice(8);
        if (!tail.length || tail[0].match(/\s/)) return tail.trimStart();
    }
    return trimmed;
}

/**
 * @param {string} raw
 * @returns {string | null}
 */
function disciplineIdFromUserText(raw) {
    const text = (raw || "").trimStart();
    if (text.startsWith("/doc")) return "doc";
    if (text.startsWith("/content")) return "content";
    for (const d of getDisciplines()) {
        const prefix = d.command;
        if (!text.startsWith(prefix)) continue;
        const tail = text.slice(prefix.length);
        if (tail.length > 0 && !tail[0].match(/\s/)) continue;
        return d.id;
    }
    return null;
}

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

/**
 * Prefixo normalizado para deduplicação de títulos truncados.
 * @param {string} title
 */
export function titlePrefixKey(title) {
    const t = String(title || "").trim();
    if (!t) return "";
    if (t.length > 45) return t.slice(0, 45);
    return t.replace(/…$/, "");
}

/**
 * Evita títulos indistinguíveis na sidebar quando truncados.
 * @param {string} candidate
 * @param {string} convId
 * @param {StoredConversation[]} conversations
 */
function ensureUniqueTitle(candidate, convId, conversations) {
    const key = titlePrefixKey(candidate);
    if (!key) return candidate;
    const collision = conversations.some(
        (c) => c.id !== convId && titlePrefixKey(c.title) === key,
    );
    if (!collision) return candidate;
    let n = 2;
    while (
        conversations.some(
            (c) =>
                c.id !== convId &&
                titlePrefixKey(c.title) === titlePrefixKey(`${candidate} (${n})`),
        )
    ) {
        n += 1;
    }
    return `${candidate} (${n})`;
}

/**
 * Infer disciplineId from last user turn with slash prefix.
 * @param {ConversationTurn[]} turns
 * @returns {string | null}
 */
export function inferDisciplineFromTurns(turns) {
    if (!Array.isArray(turns) || !turns.length) return null;
    for (let i = turns.length - 1; i >= 0; i -= 1) {
        const t = turns[i];
        if (t?.role !== "user" || !t.text) continue;
        const id = disciplineIdFromUserText(t.text);
        if (id) return id;
    }
    return null;
}

/**
 * @param {Partial<StoredConversation> & { id: string }} conv
 * @returns {StoredConversation}
 */
function normalizeConversation(conv) {
    const turns = Array.isArray(conv.turns) ? conv.turns : [];
    const disciplineId =
        typeof conv.disciplineId === "string" || conv.disciplineId === null
            ? conv.disciplineId
            : inferDisciplineFromTurns(turns);
    return {
        id: conv.id,
        title: conv.title || "Nova conversa",
        createdAt: conv.createdAt || Date.now(),
        updatedAt: conv.updatedAt || Date.now(),
        session_id: typeof conv.session_id === "string" ? conv.session_id : null,
        disciplineId,
        turns,
    };
}

/**
 * @param {string} [id] — defaults to active conversation
 * @returns {string | null}
 */
export function getConversationDiscipline(id) {
    const store = loadStore();
    const targetId = id || store.activeId;
    if (!targetId) return null;
    const conv = store.conversations.find((c) => c.id === targetId);
    if (!conv) return null;
    if (typeof conv.disciplineId === "string" || conv.disciplineId === null) {
        return conv.disciplineId;
    }
    return inferDisciplineFromTurns(conv.turns);
}

/**
 * @param {string} id
 * @param {string | null} disciplineId
 */
export function setConversationDiscipline(id, disciplineId) {
    const store = loadStore();
    const conv = store.conversations.find((c) => c.id === id);
    if (!conv) return;
    conv.disciplineId = disciplineId;
    conv.updatedAt = Date.now();
    saveStore(store);
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
            disciplineId: inferDisciplineFromTurns(turns),
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
            ? parsed.conversations.filter((c) => c && c.id).map(normalizeConversation)
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
        disciplineId: null,
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
 * @param {{ session_id?: string | null, turns: ConversationTurn[], title?: string, disciplineId?: string | null }} data
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
    if (data.disciplineId !== undefined) {
        conv.disciplineId = data.disciplineId;
    } else if (conv.disciplineId === undefined) {
        conv.disciplineId = inferDisciplineFromTurns(conv.turns);
    }
    if (data.title) conv.title = data.title;
    else {
        const firstUser = conv.turns.find((t) => t.role === "user");
        if (firstUser && (conv.title === "Nova conversa" || !conv.title)) {
            const base = titleFromFirstMessage(firstUser.text);
            conv.title = ensureUniqueTitle(base, conv.id, store.conversations);
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

/**
 * @param {string} id
 * @returns {{ deleted: StoredConversation, wasActive: boolean, nextActiveId: string | null } | null}
 */
export function deleteConversation(id) {
    const store = loadStore();
    const idx = store.conversations.findIndex((c) => c.id === id);
    if (idx === -1) return null;

    const deleted = store.conversations.splice(idx, 1)[0];
    const wasActive = store.activeId === id;

    if (wasActive) {
        if (store.conversations.length) {
            store.activeId = store.conversations[0].id;
        } else {
            const fresh = {
                id: newId(),
                title: "Nova conversa",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                session_id: null,
                disciplineId: null,
                turns: [],
            };
            store.conversations.unshift(fresh);
            store.activeId = fresh.id;
        }
    }

    saveStore(store);
    return { deleted, wasActive, nextActiveId: store.activeId };
}

/**
 * @param {StoredConversation} conv
 * @param {{ activeId?: string | null, index?: number }} [opts]
 */
export function restoreConversation(conv, opts = {}) {
    const store = loadStore();
    if (store.conversations.some((c) => c.id === conv.id)) return;
    const index =
        typeof opts.index === "number" && opts.index >= 0
            ? Math.min(opts.index, store.conversations.length)
            : 0;
    store.conversations.splice(index, 0, normalizeConversation(conv));
    if (opts.activeId !== undefined) {
        store.activeId = opts.activeId;
    }
    saveStore(store);
}

/**
 * @param {string} id
 * @param {string} title
 * @returns {boolean}
 */
export function renameConversation(id, title) {
    const store = loadStore();
    const conv = store.conversations.find((c) => c.id === id);
    if (!conv) return false;
    const trimmed = String(title || "").trim();
    if (!trimmed) return false;
    conv.title = trimmed.length > 48 ? `${trimmed.slice(0, 45)}…` : trimmed;
    conv.updatedAt = Date.now();
    saveStore(store);
    return true;
}
