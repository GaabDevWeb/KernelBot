import { ChatService } from "./api.js";
import {
    buildDisambiguationFollowUp,
    isDisambiguationGeneration,
    isStructuredHardStop,
    normalizeHardStopPayload,
    shouldMountDisambiguationChips,
    shouldMountIndexGap,
} from "./acl/parseAclMeta.js";
import { createComposer } from "./components/Composer.js";
import { createChatView } from "./components/ChatView.js";
import { mountDisambiguationChips } from "./components/DisambiguationChips.js";
import { mountIndexGapAlert } from "./components/IndexGapAlert.js";
import { createStatusBadge } from "./components/StatusBadge.js";
import { setBreadcrumbsContent, setDisambiguationHint } from "./components/MessageRow.js";
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
    /** @type {string | null} */
    let pendingChipFollowUp = null;
    /** @type {ReturnType<typeof createComposer>} */
    let composer;

    const SILO_CLASS_PREFIX = "input-area--silo-";

    function clearStructuredUiArtifacts() {
        document.querySelectorAll(".disambiguation-chips").forEach((el) => el.remove());
        document.querySelectorAll(".index-gap-alert").forEach((el) => el.remove());
    }

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

    /**
     * @param {string} [overrideText] — usado por chips de desambiguação (evita double-send via input)
     */
    async function sendMessage(overrideText) {
        if (sending) return;
        const text =
            typeof overrideText === "string" ? overrideText.trim() : input.value.trim();
        if (!text) return;

        clearStructuredUiArtifacts();

        sending = true;
        if (typeof overrideText !== "string") {
            composer.clear();
        }
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
        /** @type {'markdown' | 'structured'} */
        let turnMode = "markdown";
        let structuredHistoryLabel = "";

        const result = await chatService.sendStream(text, {
            sessionId,
            onMeta(meta) {
                const reason = String(meta?.reason || "");
                const payload = normalizeHardStopPayload(
                    reason,
                    /** @type {Record<string, unknown> | undefined} */ (meta?.payload),
                );

                if (isStructuredHardStop(meta)) {
                    turnMode = "structured";
                    bubble.innerHTML = "";
                    statusEl.classList.add("context-search-status--hidden");

                    if (shouldMountIndexGap(reason, payload, meta)) {
                        mountIndexGapAlert(bubble, payload);
                        const lesson = /** @type {{ title?: string }} */ (payload?.expected_lesson);
                        structuredHistoryLabel = `[Index gap] ${lesson?.title || "aula"}`;
                    } else if (shouldMountDisambiguationChips(reason, payload, meta)) {
                        mountDisambiguationChips(bubble, payload, {
                            onSelect(candidate) {
                                const followUp = buildDisambiguationFollowUp(candidate);
                                input.value = followUp;
                                input.dispatchEvent(new Event("input"));
                                refreshSiloUi();
                                if (sending) {
                                    pendingChipFollowUp = followUp;
                                    return;
                                }
                                void sendMessage(followUp);
                            },
                        });
                        structuredHistoryLabel = "[Desambiguação — escolha uma aula]";
                    }
                    return;
                }

                turnMode = "markdown";
                refreshPinBadge(meta);
                if (meta && typeof meta.label === "string" && meta.label) {
                    statusEl.textContent = `Analisando resumos de ${meta.label}...`;
                }
                streamSources = Array.isArray(meta?.sources) ? meta.sources : [];
                setBreadcrumbsContent(breadcrumbs, streamSources);
                setDisambiguationHint(breadcrumbs, isDisambiguationGeneration(meta));
            },
            onFirstToken() {
                statusEl.classList.add("context-search-status--hidden");
            },
            onDelta: (fullText) => {
                if (turnMode === "structured") {
                    console.debug("[ACL] onDelta ignorado (turnMode=structured)", fullText.length);
                    return;
                }
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
        } else if (turnMode === "structured") {
            history.push({
                role: "bot",
                text: structuredHistoryLabel || "[Resposta estruturada]",
            });
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
        chatView.scrollBottom();
        sending = false;

        const deferred = pendingChipFollowUp;
        pendingChipFollowUp = null;
        if (deferred) {
            void sendMessage(deferred);
        } else {
            composer.focus();
        }
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
