import { appendMessageRowWithMeta } from "../chat/restoreTurn.js";
import { appendMessageRow, createStreamingBotRow } from "./MessageRow.js";
import { syncBodyUiState } from "../utils/uiState.js";

const LANDING_CROSSFADE_MS = 250;
const SCROLL_BOTTOM_THRESHOLD = 80;

/**
 * @param {{ chatBox: HTMLElement, emptyState: HTMLElement | null, renderMarkdown: (t: string) => string, sourceHandlers?: { onPinSource?: (d: Record<string, unknown>) => void }, chipHandlers?: { onSelect: (c: { title?: string, discipline?: string, slug?: string }) => void }, onRegenerate?: () => void }} opts
 */
export function createChatView({
    chatBox,
    emptyState,
    renderMarkdown,
    sourceHandlers,
    chipHandlers,
    onRegenerate,
}) {
    /** @type {HTMLButtonElement | null} */
    let scrollFab = null;

    function positionScrollFab() {
        const fab = scrollFab;
        if (!fab || fab.hidden) return;

        const inputArea = document.querySelector(".input-area");
        if (!inputArea) return;

        const inputRect = inputArea.getBoundingClientRect();
        const chatRect = chatBox.getBoundingClientRect();
        const rootStyles = getComputedStyle(document.documentElement);
        const readMax = parseFloat(rootStyles.getPropertyValue("--chat-read-max")) || 680;
        const chatStyles = getComputedStyle(chatBox);
        const padX =
            (parseFloat(chatStyles.paddingLeft) || 0) +
            (parseFloat(chatStyles.paddingRight) || 0);
        const innerW = Math.max(0, chatRect.width - padX);
        const columnWidth = Math.min(readMax, innerW * 0.82);
        const padLeft = parseFloat(chatStyles.paddingLeft) || 0;
        const columnRight = chatRect.left + padLeft + columnWidth;

        const size = 44;
        const gap = 8;

        fab.style.top = `${Math.max(8, inputRect.top - gap - size)}px`;
        fab.style.left = `${Math.max(8, columnRight - size)}px`;
        fab.style.bottom = "auto";
        fab.style.right = "auto";
    }

    function ensureScrollFab() {
        if (scrollFab && document.body.contains(scrollFab)) return scrollFab;
        scrollFab = document.createElement("button");
        scrollFab.type = "button";
        scrollFab.className = "scroll-to-bottom-fab";
        scrollFab.hidden = true;
        scrollFab.setAttribute("aria-label", "Ir para o fim da conversa");
        scrollFab.title = "Ir para o fim";
        scrollFab.innerHTML =
            '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 3v8M4 7l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
        scrollFab.addEventListener("click", () => scrollBottom(true));
        document.body.appendChild(scrollFab);

        const appEl = document.querySelector(".app");
        const inputArea = document.querySelector(".input-area");
        const reposition = () => positionScrollFab();
        window.addEventListener("resize", reposition, { passive: true });
        appEl && new ResizeObserver(reposition).observe(appEl);
        inputArea && new ResizeObserver(reposition).observe(inputArea);
        document.getElementById("conversation-sidebar")?.addEventListener("transitionend", reposition);

        return scrollFab;
    }

    function updateScrollFab() {
        const fab = ensureScrollFab();
        const distance = chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight;
        fab.hidden = distance <= SCROLL_BOTTOM_THRESHOLD;
        if (!fab.hidden) positionScrollFab();
    }

        chatBox.addEventListener("scroll", updateScrollFab, { passive: true });
        new MutationObserver(() => updateScrollFab()).observe(chatBox, {
            childList: true,
            subtree: true,
        });

    function showLanding() {
        if (!emptyState) {
            syncBodyUiState();
            return;
        }
        emptyState.style.display = "flex";
        emptyState.classList.remove("empty-state--dismissed");
        syncBodyUiState();
        window.dispatchEvent(new CustomEvent("kernel:show-landing"));
    }

    function hideEmptyState() {
        if (!emptyState || emptyState.style.display === "none") {
            syncBodyUiState();
            return;
        }
        if (!emptyState.classList.contains("empty-state--dismissed")) {
            emptyState.classList.add("empty-state--dismissed");
            window.setTimeout(() => {
                if (emptyState) emptyState.style.display = "none";
                syncBodyUiState();
                window.dispatchEvent(new CustomEvent("kernel:chat-active"));
            }, LANDING_CROSSFADE_MS);
        }
        syncBodyUiState();
    }

    function scrollBottom(instant = false) {
        chatBox.scrollTo({
            top: chatBox.scrollHeight,
            behavior: instant ? "auto" : "smooth",
        });
        requestAnimationFrame(updateScrollFab);
    }

    function toolbarHandlersForRole(role, text) {
        const botRows = chatBox.querySelectorAll(".message-row.bot");
        const isLastBot = role === "bot" && botRows.length === 0;
        return {
            onRegenerate,
            isLastBot: role === "bot" ? isLastBot : false,
        };
    }

    /**
     * @param {'user'|'bot'} role
     * @param {string} text
     * @param {boolean} [isError]
     * @param {boolean} [animated]
     * @param {string[] | undefined} [sources]
     * @param {Array<Record<string, unknown>> | undefined} [sourceDetails]
     * @param {import('../chat/restoreTurn.js').TurnMeta | undefined} [turnMeta]
     */
    function appendMessage(
        role,
        text,
        isError = false,
        animated = true,
        sources,
        sourceDetails,
        turnMeta,
    ) {
        hideEmptyState();
        const toolbarHandlers = toolbarHandlersForRole(role, text);
        if (role === "bot" && (turnMeta || sources?.length || sourceDetails?.length)) {
            return appendMessageRowWithMeta(chatBox, {
                role,
                text,
                isError,
                sources,
                sourceDetails,
                turnMeta,
                renderMarkdown,
                animated,
                scrollBottom,
                sourceHandlers,
                chipHandlers,
                toolbarHandlers,
            });
        }
        return appendMessageRow(chatBox, {
            role,
            text,
            isError,
            sources,
            sourceDetails,
            renderMarkdown,
            animated,
            scrollBottom,
            sourceHandlers,
            toolbarHandlers,
        });
    }

    function renderSavedHistory(hist) {
        if (!hist.length) return;
        hideEmptyState();
        hist.forEach(({ role, text, sources, sourceDetails, turnMeta }, index) => {
            const isLastBot =
                role === "bot" &&
                !hist.slice(index + 1).some((t) => t.role === "bot");
            if (role === "bot" && (turnMeta || sources?.length || sourceDetails?.length)) {
                appendMessageRowWithMeta(chatBox, {
                    role,
                    text,
                    isError: false,
                    sources,
                    sourceDetails,
                    turnMeta,
                    renderMarkdown,
                    animated: false,
                    scrollBottom,
                    sourceHandlers,
                    chipHandlers,
                    toolbarHandlers: { onRegenerate, isLastBot },
                });
            } else {
                appendMessageRow(chatBox, {
                    role,
                    text,
                    isError: false,
                    sources,
                    sourceDetails,
                    renderMarkdown,
                    animated: false,
                    scrollBottom,
                    sourceHandlers,
                    toolbarHandlers: { onRegenerate, isLastBot: role === "bot" && isLastBot },
                });
            }
        });
        syncBodyUiState();
        updateScrollFab();
    }

    function clearChat() {
        chatBox.querySelectorAll(".message-row").forEach((el) => el.remove());
        chatBox.querySelectorAll(".context-search-status").forEach((el) => el.remove());
        updateScrollFab();
    }

    function removeLastBotRow() {
        const rows = chatBox.querySelectorAll(".message-row.bot");
        const last = rows[rows.length - 1];
        last?.remove();
    }

    function startBotStream() {
        hideEmptyState();
        return createStreamingBotRow(chatBox, scrollBottom);
    }

    return {
        appendMessage,
        renderSavedHistory,
        clearChat,
        removeLastBotRow,
        startBotStream,
        scrollBottom,
        hideEmptyState,
        showLanding,
        updateScrollFab,
    };
}
