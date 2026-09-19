import { isChatActive, isLanding } from "./uiState.js";

export const HEADER_CONVERSATION_LABEL_MAX = 32;

/**
 * @param {string} title
 */
export function formatConversationLabelTitle(title) {
    const t = String(title || "Nova conversa").trim() || "Nova conversa";
    if (t.length <= HEADER_CONVERSATION_LABEL_MAX) return t;
    return `${t.slice(0, HEADER_CONVERSATION_LABEL_MAX - 1)}…`;
}

/** @returns {HTMLElement | null} */
export function getHeaderConversationLabelEl() {
    return document.getElementById("header-conversation-label");
}

/** @returns {HTMLImageElement | null} */
export function getHeaderConversationAvatarEl() {
    return /** @type {HTMLImageElement | null} */ (
        document.getElementById("header-conversation-avatar")
    );
}

export function refreshHeaderConversationLabelVisibility() {
    const el = getHeaderConversationLabelEl();
    const avatarEl = getHeaderConversationAvatarEl();

    const sidebar = document.getElementById("conversation-sidebar");
    const collapsed = sidebar?.classList.contains("conversation-sidebar--collapsed") ?? false;
    const show = !isLanding() && (isChatActive() || collapsed);
    if (el) el.hidden = !show;
    if (avatarEl) avatarEl.hidden = !show || !avatarEl.src;
}

/**
 * @param {string} title
 * @param {string} [avatarUrl]
 */
export function updateHeaderConversationLabel(title, avatarUrl) {
    const el = getHeaderConversationLabelEl();
    if (el) {
        const full = String(title || "Nova conversa").trim() || "Nova conversa";
        el.textContent = formatConversationLabelTitle(full);
        el.title = full;
    }
    const avatarEl = getHeaderConversationAvatarEl();
    if (avatarEl && avatarUrl) {
        avatarEl.src = avatarUrl;
    }
    refreshHeaderConversationLabelVisibility();
}
