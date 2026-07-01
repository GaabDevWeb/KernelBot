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

/** Garante composer visível após skip da landing (F5 com histórico, deep link, etc.). */
export function revealComposerChrome() {
    document.querySelectorAll(".entrance-init-hidden").forEach((el) => {
        el.classList.remove("entrance-init-hidden");
    });
    const inputArea = document.querySelector(".input-area");
    const gsap = typeof window.gsap !== "undefined" ? window.gsap : null;
    if (inputArea && gsap) {
        gsap.set(inputArea, { autoAlpha: 1, y: 0, clearProps: "transform" });
    }
}
