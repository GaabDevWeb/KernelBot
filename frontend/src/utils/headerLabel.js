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

export function refreshHeaderConversationLabelVisibility() {
    const el = getHeaderConversationLabelEl();
    if (!el) return;

    const sidebar = document.getElementById("conversation-sidebar");
    const collapsed = sidebar?.classList.contains("conversation-sidebar--collapsed") ?? false;
    const show = !isLanding() && (isChatActive() || collapsed);
    el.hidden = !show;
}

/**
 * @param {string} title
 */
export function updateHeaderConversationLabel(title) {
    const el = getHeaderConversationLabelEl();
    if (!el) return;
    const full = String(title || "Nova conversa").trim() || "Nova conversa";
    el.textContent = formatConversationLabelTitle(full);
    el.title = full;
    refreshHeaderConversationLabelVisibility();
}
