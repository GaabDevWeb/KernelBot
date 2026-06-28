import { appendMessageRowWithMeta } from "../chat/restoreTurn.js";
import { appendMessageRow, createStreamingBotRow } from "./MessageRow.js";
import { syncBodyUiState } from "../utils/uiState.js";

/**
 * @param {{ chatBox: HTMLElement, emptyState: HTMLElement | null, renderMarkdown: (t: string) => string, sourceHandlers?: { onPinSource?: (d: Record<string, unknown>) => void }, chipHandlers?: { onSelect: (c: { title?: string, discipline?: string, slug?: string }) => void } }} opts
 */
export function createChatView({
    chatBox,
    emptyState,
    renderMarkdown,
    sourceHandlers,
    chipHandlers,
}) {
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
            }, 200);
        }
        syncBodyUiState();
    }

    function scrollBottom() {
        chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });
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
        });
    }

    function renderSavedHistory(hist) {
        if (!hist.length) return;
        hideEmptyState();
        hist.forEach(({ role, text, sources, sourceDetails, turnMeta }) =>
            appendMessage(role, text, false, false, sources, sourceDetails, turnMeta),
        );
        syncBodyUiState();
    }

    function clearChat() {
        chatBox.querySelectorAll(".message-row").forEach((el) => el.remove());
        chatBox.querySelectorAll(".context-search-status").forEach((el) => el.remove());
        if (emptyState) {
            emptyState.style.display = "";
            emptyState.classList.remove("empty-state--dismissed");
        }
        syncBodyUiState();
    }

    function startBotStream() {
        hideEmptyState();
        return createStreamingBotRow(chatBox, scrollBottom);
    }

    return {
        appendMessage,
        renderSavedHistory,
        clearChat,
        startBotStream,
        scrollBottom,
        hideEmptyState,
    };
}
