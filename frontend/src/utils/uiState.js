import { refreshHeaderConversationLabelVisibility } from "./headerLabel.js";

/** @returns {HTMLElement | null} */
export function getEmptyStateEl() {
    return document.getElementById("empty-state");
}

/** Landing: empty-state visível (hero / primeira impressão). */
export function isLanding() {
    const el = getEmptyStateEl();
    if (!el) return false;
    if (el.style.display === "none") return false;
    if (el.classList.contains("empty-state--dismissed")) return false;
    return true;
}

/** ChatActive: pelo menos uma mensagem no histórico visível. */
export function isChatActive() {
    const chat = document.getElementById("chat");
    if (!chat) return false;
    return chat.querySelector(".message-row") !== null;
}

/** Sincroniza classe no body para motion/CSS contextual. */
export function syncBodyUiState() {
    document.body.classList.toggle("chat-active", isChatActive());
    document.body.classList.toggle("ui-landing", isLanding());
    refreshHeaderConversationLabelVisibility();
}
