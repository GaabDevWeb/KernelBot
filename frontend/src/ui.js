import { ChatService } from "./api.js";
import { createComposer } from "./components/Composer.js";
import { createChatView } from "./components/ChatView.js";
import { createStatusBadge } from "./components/StatusBadge.js";
import { setBreadcrumbsContent } from "./components/MessageRow.js";
import { siloClassSuffix, siloDisplayName, immediateContextLabel } from "./utils/contextLabel.js";
import { loadHistory, saveHistory } from "./utils/history.js";
import { getOrCreateSessionId } from "./utils/sessionId.js";
import { highlightCodeBlocks, renderMarkdown } from "./utils/markdown.js";

export function init() {
    const chatBox = document.getElementById("chat");
    const input = document.getElementById("message-input");
    const sendBtn = document.getElementById("send-button");
    const emptyState = document.getElementById("empty-state");
    const statusBadge = document.getElementById("status-badge");
    const inputArea = document.querySelector(".input-area");
    const siloPill = document.getElementById("silo-pill");
    const pinBadge = document.getElementById("context-pin-badge");
    const sessionId = getOrCreateSessionId();

    if (!chatBox || !input || !sendBtn || !statusBadge) {
        console.error("[ACL] DOM esperado ausente (chat, input, send ou status).");
        return;
    }

    const chatService = new ChatService();
    const status = createStatusBadge(statusBadge);
    const chatView = createChatView({ chatBox, emptyState, renderMarkdown });

    let sending = false;
    /** @type {ReturnType<typeof createComposer>} */
    let composer;

    const SILO_CLASS_PREFIX = "input-area--silo-";

    function refreshPinBadge(meta) {
        if (!pinBadge) return;
        const active = Boolean(meta?.pinned_active);
        const label = typeof meta?.pinned_display === "string" ? meta.pinned_display.trim() : "";
        if (active && label) {
            pinBadge.hidden = false;
            pinBadge.textContent = `Contexto: ${label}`;
        } else {
            pinBadge.hidden = true;
            pinBadge.textContent = "";
        }
    }

    function refreshSiloUi() {
        if (!inputArea) return;
        [...inputArea.classList].forEach((c) => {
            if (c === "input-area--silo" || c.startsWith(SILO_CLASS_PREFIX)) {
                inputArea.classList.remove(c);
            }
        });
        const suffix = siloClassSuffix(input.value);
        if (suffix && siloPill) {
            inputArea.classList.add("input-area--silo", SILO_CLASS_PREFIX + suffix);
            siloPill.hidden = false;
            const name = siloDisplayName(input.value);
            siloPill.textContent = name ? `Silo: ${name}` : "";
        } else if (siloPill) {
            siloPill.hidden = true;
            siloPill.textContent = "";
        }
    }

    async function sendMessage() {
        if (sending) return;
        const text = input.value.trim();
        if (!text) return;

        sending = true;
        composer.clear();
        composer.setEnabled(false);
        status.setProcessing();

        chatView.appendMessage("user", text);

        const history = loadHistory();
        history.push({ role: "user", text });
        saveHistory(history);

        const statusEl = document.createElement("div");
        statusEl.className = "context-search-status";
        statusEl.textContent = `Analisando resumos de ${immediateContextLabel(text)}...`;
        chatBox.appendChild(statusEl);

        const { bubble, breadcrumbs } = chatView.startBotStream();

        let streamSources = [];

        const result = await chatService.sendStream(text, {
            sessionId,
            onMeta(meta) {
                refreshPinBadge(meta);
                if (meta && typeof meta.label === "string" && meta.label) {
                    statusEl.textContent = `Analisando resumos de ${meta.label}...`;
                }
                streamSources = Array.isArray(meta?.sources) ? meta.sources : [];
                setBreadcrumbsContent(breadcrumbs, streamSources);
            },
            onFirstToken() {
                statusEl.classList.add("context-search-status--hidden");
            },
            onDelta: (fullText) => {
                bubble.innerHTML = renderMarkdown(fullText);
                chatView.scrollBottom();
            },
        });

        if (!result.ok || result.isError || !String(result.fullText || "").length) {
            statusEl.classList.add("context-search-status--hidden");
        }

        bubble.classList.remove("cursor-blink");

        if (!result.ok) {
            bubble.classList.add("error");
            bubble.textContent = result.message;
            history.push({ role: "bot", text: result.message });
        } else if (result.isError) {
            bubble.classList.add("error");
            bubble.textContent = result.fullText;
            history.push({ role: "bot", text: result.fullText });
        } else {
            bubble.innerHTML = renderMarkdown(result.fullText);
            highlightCodeBlocks(bubble);
            history.push({
                role: "bot",
                text: result.fullText,
                ...(streamSources.length ? { sources: streamSources } : {}),
            });
        }

        saveHistory(history);

        composer.setEnabled(true);
        status.setOnline();
        composer.focus();
        chatView.scrollBottom();
        sending = false;
    }

    composer = createComposer({
        input,
        sendButton: sendBtn,
        onSend: sendMessage,
        pillsRoot: document,
    });

    input.addEventListener("input", refreshSiloUi);
    refreshSiloUi();

    chatView.renderSavedHistory(loadHistory());
    composer.focus();
}
