import { appendMessageRow, createStreamingBotRow } from "./MessageRow.js";

/**
 * @param {{ chatBox: HTMLElement, emptyState: HTMLElement | null, renderMarkdown: (t: string) => string }} opts
 */
export function createChatView({ chatBox, emptyState, renderMarkdown }) {
    function hideEmptyState() {
        if (emptyState) emptyState.style.display = "none";
    }

    function scrollBottom() {
        chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });
    }

    /**
     * @param {'user'|'bot'} role
     * @param {string} text
     * @param {boolean} [isError]
     * @param {boolean} [animated]
     * @param {string[] | undefined} [sources] — breadcrumbs (apenas bot)
     */
    function appendMessage(role, text, isError = false, animated = true, sources) {
        hideEmptyState();
        return appendMessageRow(chatBox, {
            role,
            text,
            isError,
            sources,
            renderMarkdown,
            animated,
            scrollBottom,
        });
    }

    function renderSavedHistory(hist) {
        if (!hist.length) return;
        hideEmptyState();
        hist.forEach(({ role, text, sources }) =>
            appendMessage(role, text, false, false, sources),
        );
    }

    function startBotStream() {
        hideEmptyState();
        return createStreamingBotRow(chatBox, scrollBottom);
    }

    return {
        appendMessage,
        renderSavedHistory,
        startBotStream,
        scrollBottom,
        hideEmptyState,
    };
}
