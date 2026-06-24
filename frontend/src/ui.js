import { ChatService } from "./api.js";
import {
    disambiguationOptionsFromMeta,
    stripAmbiguityMarkupFromText,
} from "./acl/parseAmbiguityOptions.js";
import { buildTurnMeta } from "./chat/restoreTurn.js";
import { createComposerController } from "./chat/ComposerController.js";
import { createMetaRenderer } from "./chat/MetaRenderer.js";
import {
    buildDisambiguationFollowUp,
    isDisambiguationGeneration,
    isPostGenerationAdvisory,
    isPostGenerationOverride,
    isStructuredHardStop,
    normalizeHardStopPayload,
    resolveTurnHintVariant,
    sourcesNoteFromMeta,
    shouldMountDisambiguationChips,
    shouldMountIndexGap,
} from "./acl/parseAclMeta.js";
import { createSlashCommandMenu } from "./components/SlashCommandMenu.js";
import { createConversationSidebar } from "./components/ConversationSidebar.js";
import { createContextWindowNotice } from "./components/ContextWindowNotice.js";
import { createComposer } from "./components/Composer.js";
import { createChatView } from "./components/ChatView.js";
import {
    freezeDisambiguationChips,
    invalidateDisambiguationChips,
    mountDisambiguationChips,
    syncDisambiguationChips,
} from "./components/DisambiguationChips.js";
import {
    AMBIGUITY_STREAM_PLACEHOLDER,
    finalizeAmbiguityStreamDisplay,
    mergeDisambiguationOptions,
    parseCompleteOptionsIncremental,
    processAmbiguityStreamDisplay,
    STREAM_TRUNCATED_AMBIGUITY_MSG,
} from "./acl/ambiguityStreamBuffer.js";
import { mountIndexGapAlert } from "./components/IndexGapAlert.js";
import { createStatusBadge } from "./components/StatusBadge.js";
import {
    setBreadcrumbsContent,
    setTurnHintBadge,
} from "./components/MessageRow.js";
import { groundingPolicyLabel, reasonLabel } from "./acl/reasonLabel.js";
import { immediateContextLabel } from "./utils/contextLabel.js";
import {
    getHistoryForApi,
    loadConversation,
    loadHistory,
    saveHistory,
} from "./utils/history.js";
import { createConversation, getActiveConversation } from "./utils/conversations.js";
import { applyDisciplineDeepLink } from "./utils/deepLink.js";
import { getOrCreateSessionId, regenerateSessionId } from "./utils/sessionId.js";
import { highlightCodeBlocks, renderMarkdown } from "./utils/markdown.js";
import { createGlobe } from "./globe.js";

export function init() {
    const chatBox = document.getElementById("chat");
    const input = document.getElementById("message-input");
    const sendBtn = document.getElementById("send-button");
    const emptyState = document.getElementById("empty-state");
    const statusBadge = document.getElementById("status-badge");
    const inputArea = document.querySelector(".input-area");
    const siloPill = document.getElementById("silo-pill");
    const pinBadge = document.getElementById("context-pin-badge");
    const contextStack = document.getElementById("context-stack");
    const newChatBtn = document.getElementById("new-chat-button");
    const activeDisciplineBadge = document.getElementById("active-discipline-badge");
    const scopeBtn = document.getElementById("scope-btn");
    const contextWindowNoticeEl = document.getElementById("context-window-notice");
    const composerWrap = document.getElementById("composer-wrap");
    const sidebarEl = document.getElementById("conversation-sidebar");
    const conversationList = document.getElementById("conversation-list");
    const sidebarOverlay = document.getElementById("sidebar-overlay");
    const sidebarToggle = document.getElementById("sidebar-toggle");
    const sidebarNewBtn = document.getElementById("sidebar-new-chat");
    let sessionId = getOrCreateSessionId();

    if (!chatBox || !input || !sendBtn || !statusBadge) {
        console.error("[ACL] DOM esperado ausente (chat, input, send ou status).");
        return;
    }

    const chatService = new ChatService();
    const status = createStatusBadge(statusBadge);
    const contextWindowNotice = createContextWindowNotice(contextWindowNoticeEl);

    function refreshContextWindowNotice(turnCount) {
        contextWindowNotice.refresh(turnCount);
    }

    function pinFromSource(detail) {
        const followUp = buildDisambiguationFollowUp({
            discipline: String(detail?.discipline || ""),
            slug: String(detail?.slug || ""),
            title: String(detail?.lesson_title || ""),
        });
        input.value = followUp;
        input.dispatchEvent(new Event("input"));
        refreshSiloUi();
        if (sending) {
            pendingChipFollowUp = followUp;
            return;
        }
        void sendMessage(followUp);
    }

    const sourceHandlers = { onPinSource: pinFromSource };

    function chipSelectFromRestore(candidate) {
        const followUp = buildDisambiguationFollowUp(candidate);
        input.value = followUp;
        input.dispatchEvent(new Event("input"));
        refreshSiloUi();
        if (sending) {
            pendingChipFollowUp = followUp;
            return;
        }
        void sendMessage(followUp);
    }

    const chipHandlers = { onSelect: chipSelectFromRestore };

    const chatView = createChatView({
        chatBox,
        emptyState,
        renderMarkdown,
        sourceHandlers,
        chipHandlers,
    });

    let sending = false;
    /** @type {string | null} */
    let pendingChipFollowUp = null;
    /** @type {ReturnType<typeof createComposer>} */
    let composer;

    function refreshContextStack() {
        if (!contextStack) return;
        const siloVisible = siloPill && !siloPill.hidden;
        const pinVisible = pinBadge && !pinBadge.hidden;
        contextStack.hidden = !(siloVisible || pinVisible);
    }

    const metaRenderer = createMetaRenderer({ pinBadge, contextStack, refreshContextStack });
    const {
        refreshPinBadge,
        hidePinBadge,
        applyTurnHintFromMeta,
        refreshStreamContextUi,
    } = metaRenderer;

    const { refreshSiloUi } = createComposerController({
        input,
        inputArea,
        siloPill,
        activeDisciplineBadge,
        scopeBtn,
        contextStack,
        refreshContextStack,
    });

    function clearStructuredUiArtifacts() {
        document.querySelectorAll(".disambiguation-chips").forEach((el) => el.remove());
        document.querySelectorAll(".index-gap-alert").forEach((el) => el.remove());
    }

    /** @type {ReturnType<typeof createConversationSidebar> | null} */
    let sidebar = null;

    function reloadConversationView() {
        sessionId = getOrCreateSessionId();
        chatView.clearChat();
        chatView.renderSavedHistory(loadHistory());
        refreshContextWindowNotice(loadConversation().turns.length);
        hidePinBadge();
        refreshSiloUi();
        sidebar?.render();
    }

    function finishConversationReset() {
        createConversation({ activate: true });
        sessionId = regenerateSessionId();
        chatView.clearChat();
        hidePinBadge();
        refreshSiloUi();
        refreshContextWindowNotice(0);
        sidebar?.render();
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

        const isResetCmd = /^\/(?:reset|limpar)\b/i.test(text);
        const historyForApi = isResetCmd ? [] : getHistoryForApi();

        chatView.appendMessage("user", text);

        const history = loadHistory();
        history.push({ role: "user", text });

        const statusEl = document.createElement("div");
        statusEl.className = "context-search-status thinking-indicator";
        const thinkingCanvas = document.createElement("canvas");
        thinkingCanvas.className = "thinking-globe";
        thinkingCanvas.setAttribute("aria-hidden", "true");
        const thinkingLabel = document.createElement("span");
        thinkingLabel.textContent = `Analisando ${immediateContextLabel(text)}...`;
        statusEl.append(thinkingCanvas, thinkingLabel);
        chatBox.appendChild(statusEl);

        const thinkingGlobe = createGlobe(thinkingCanvas, {
            sizeTo: "self",
            variant: "thinking",
            formed: true,
            spin: true,
            spinSpeed: 0.55,
            particles: false,
        });
        thinkingGlobe.state.scale = 1.18;

        const {
            bubble,
            breadcrumbs,
            prose: proseEl,
            ambiguitySlot,
            postAmbiguity: postAmbiguityEl,
        } = chatView.startBotStream();

        let streamSources = [];
        /** @type {Array<Record<string, unknown>>} */
        let streamSourceDetails = [];
        /** @type {'markdown' | 'structured' | 'disambiguation_chips'} */
        let turnMode = "markdown";
        let structuredHistoryLabel = "";
        /** @type {Record<string, unknown> | null} */
        let lastMeta = null;
        let chipsMounted = false;
        let chipsInvalidated = false;
        let streamFullText = "";
        /** @type {Array<{ title: string, discipline: string, slug: string }> | null} */
        let pendingMetaOptions = null;
        /** Chips montados após abort/timeout de inatividade (nova pesquisa autónoma no clique). */
        let turnRescuedFromStream = false;
        /** @type {Record<string, unknown> | null} */
        let indexGapPayload = null;
        /** @type {Array<{ title: string, discipline: string, slug: string }>} */
        let savedDisambiguationCandidates = [];

        function buildBotTurnMeta(answerText = "") {
            return buildTurnMeta({
                turnMode,
                lastMeta,
                chipsMounted,
                chipsInvalidated,
                turnRescuedFromStream,
                disambiguationCandidates: savedDisambiguationCandidates,
                indexGapPayload,
                answerText,
                groundingPolicyLabel,
                reasonLabel,
                sourcesNoteFromMeta: metaSourcesNote,
                resolveTurnHintVariant,
                isPostGenerationOverride,
            });
        }

        function botHistoryEntry(text, answerText = "") {
            const turnMeta = buildBotTurnMeta(answerText);
            return {
                role: "bot",
                text,
                ...(streamSources.length ? { sources: streamSources } : {}),
                ...(streamSourceDetails.length ? { sourceDetails: streamSourceDetails } : {}),
                ...(turnMeta ? { turnMeta } : {}),
            };
        }

        function ambiguityPlaceholderHtml() {
            return `<p class="ambiguity-stream-placeholder">${AMBIGUITY_STREAM_PLACEHOLDER}</p>`;
        }

        function chipsMountTarget() {
            return ambiguitySlot || bubble;
        }

        function clearAmbiguityPlaceholder() {
            ambiguitySlot?.querySelector(".ambiguity-stream-placeholder")?.remove();
            ambiguitySlot?.classList.remove("stream-ambiguity-slot--reserved");
        }

        function showAmbiguityPlaceholder() {
            if (!ambiguitySlot) return;
            if (!ambiguitySlot.querySelector(".ambiguity-stream-placeholder")) {
                ambiguitySlot.insertAdjacentHTML("afterbegin", ambiguityPlaceholderHtml());
            }
            ambiguitySlot.classList.add("stream-ambiguity-slot--reserved");
        }

        function chipSelectHandler() {
            return {
                onSelect: (candidate) => {
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
            };
        }

        /**
         * Chips fechados (`<option …/>` ou `<option …></option>`) assim que o parser os vê.
         * @param {Array<{ title: string, discipline: string, slug: string }>} options
         * @param {{ rescued?: boolean }} [opts]
         */
        function syncIncrementalChips(options, opts = {}) {
            if (chipsInvalidated || !options.length) return;
            if (!lastMeta || !isDisambiguationGeneration(lastMeta)) return;
            clearAmbiguityPlaceholder();
            const rescued = Boolean(opts.rescued || turnRescuedFromStream);
            const wrap = syncDisambiguationChips(chipsMountTarget(), options, {
                ...chipSelectHandler(),
                rescued,
            });
            if (wrap) {
                chipsMounted = true;
                turnMode = "disambiguation_chips";
                structuredHistoryLabel = rescued
                    ? "[Desambiguação recuperada — escolha uma aula]"
                    : "[Desambiguação — escolha uma aula]";
                savedDisambiguationCandidates = options;
            }
        }

        /**
         * intro → chips (incrementais) → texto pós-XML. Placeholder só com bloco aberto e zero opções fechadas.
         * @param {ReturnType<typeof processAmbiguityStreamDisplay>} parsed
         * @param {Array<{ title: string, discipline: string, slug: string }>} incrementalOptions
         */
        function renderStreamBubble(parsed, incrementalOptions = []) {
            const { proseBefore, proseAfter, insideOpenBlock, blockClosed } = parsed;
            if (proseEl) {
                proseEl.innerHTML = proseBefore ? renderMarkdown(proseBefore) : "";
            }
            if (postAmbiguityEl) {
                postAmbiguityEl.innerHTML = proseAfter ? renderMarkdown(proseAfter) : "";
            }

            const canStreamChips =
                lastMeta &&
                isDisambiguationGeneration(lastMeta) &&
                !chipsInvalidated &&
                !isPostGenerationOverride(lastMeta);

            if (canStreamChips && incrementalOptions.length) {
                syncIncrementalChips(incrementalOptions);
            }

            if (!ambiguitySlot) {
                const legacy =
                    (proseBefore ? renderMarkdown(proseBefore) : "") +
                    (insideOpenBlock && !incrementalOptions.length
                        ? ambiguityPlaceholderHtml()
                        : "") +
                    (proseAfter ? renderMarkdown(proseAfter) : "");
                bubble.innerHTML = legacy || "";
                return;
            }

            if (blockClosed || incrementalOptions.length) {
                clearAmbiguityPlaceholder();
            } else if (insideOpenBlock) {
                showAmbiguityPlaceholder();
            } else if (!chipsMounted) {
                clearAmbiguityPlaceholder();
                ambiguitySlot.replaceChildren();
            }
        }

        /**
         * Chips só após fecho do stream — uma única montagem (meta + parse final).
         * @param {string} fullText
         */
        function commitDisambiguationUi(fullText) {
            const finalized = finalizeAmbiguityStreamDisplay(fullText);
            const incremental = parseCompleteOptionsIncremental(fullText);

            if (isPostGenerationOverride(lastMeta)) {
                if (postAmbiguityEl) postAmbiguityEl.replaceChildren();
                renderStreamBubble(finalized, []);
                return finalized;
            }

            if (!chipsInvalidated && lastMeta && isDisambiguationGeneration(lastMeta)) {
                const metaOpts =
                    pendingMetaOptions ?? disambiguationOptionsFromMeta(lastMeta);
                const options = mergeDisambiguationOptions(
                    metaOpts,
                    mergeDisambiguationOptions(incremental, finalized.options),
                );
                renderStreamBubble(finalized, incremental);
                if (options.length) {
                    syncIncrementalChips(options);
                    setTurnHintBadge(breadcrumbs, "disambiguation");
                    return { ...finalized, options };
                }
            }

            renderStreamBubble(finalized, incremental);
            return finalized;
        }

        /**
         * @param {string} fullText
         * @param {{ aborted?: boolean, stalled?: boolean }} [opts]
         */
        function finalizeTurnFromStream(fullText, opts = {}) {
            const finalized = finalizeAmbiguityStreamDisplay(fullText);
            const incremental = parseCompleteOptionsIncremental(fullText);
            const metaOpts = pendingMetaOptions ?? [];
            const rescued = mergeDisambiguationOptions(
                metaOpts,
                mergeDisambiguationOptions(incremental, finalized.options),
            );

            if (isPostGenerationOverride(lastMeta)) {
                commitDisambiguationUi(fullText);
                return finalized;
            }

            if (
                !chipsInvalidated &&
                lastMeta &&
                isDisambiguationGeneration(lastMeta) &&
                rescued.length
            ) {
                if (opts.stalled || opts.aborted) {
                    turnRescuedFromStream = true;
                }
                clearAmbiguityPlaceholder();
                renderStreamBubble(finalized, incremental);
                syncIncrementalChips(rescued, { rescued: turnRescuedFromStream });
                if (opts.stalled || opts.aborted) {
                    const note = document.createElement("p");
                    note.className = "stream-truncated-msg stream-truncated-msg--inline";
                    note.textContent = opts.stalled
                        ? "Ligação instável — opções recuperadas do texto parcial."
                        : "Resposta interrompida — opções recuperadas do texto parcial.";
                    ambiguitySlot?.appendChild(note);
                }
                setTurnHintBadge(breadcrumbs, "disambiguation");
                pendingMetaOptions = null;
                return { ...finalized, options: rescued };
            }

            const committed = commitDisambiguationUi(fullText);

            if (committed.insideOpenBlock && committed.streamTruncated && !chipsMounted) {
                clearAmbiguityPlaceholder();
                const msg = opts.stalled
                    ? `Ligação instável (sem dados há ~45s). ${STREAM_TRUNCATED_AMBIGUITY_MSG}`
                    : opts.aborted
                      ? `Ligação interrompida. ${STREAM_TRUNCATED_AMBIGUITY_MSG}`
                      : STREAM_TRUNCATED_AMBIGUITY_MSG;
                if (ambiguitySlot) {
                    ambiguitySlot.innerHTML = `<p class="stream-truncated-msg">${msg}</p>`;
                }
                setTurnHintBadge(breadcrumbs, "none");
            }

            pendingMetaOptions = null;
            return committed;
        }

        function mountChipsFromPayload(payload) {
            if (!payload || chipsInvalidated) return;
            clearAmbiguityPlaceholder();
            syncDisambiguationChips(chipsMountTarget(), payload.suggested_candidates, chipSelectHandler());
            chipsMounted = true;
            turnMode = "disambiguation_chips";
            structuredHistoryLabel = "[Desambiguação — escolha uma aula]";
            savedDisambiguationCandidates = Array.isArray(payload.suggested_candidates)
                ? payload.suggested_candidates.map((c) => ({
                      title: String(c?.title || c?.slug || "Aula"),
                      discipline: String(c?.discipline || ""),
                      slug: String(c?.slug || ""),
                  }))
                : [];
        }

        /**
         * @param {Record<string, unknown>} meta
         */
        function applyMetaUi(meta) {
            lastMeta = meta;
            const reason = String(meta?.reason || "");
            const payload = normalizeHardStopPayload(
                reason,
                /** @type {Record<string, unknown> | undefined} */ (meta?.payload),
            );

            if (isPostGenerationOverride(meta)) {
                turnMode = "markdown";
                chipsInvalidated = true;
                chipsMounted = false;
                pendingMetaOptions = null;
                pendingChipFollowUp = null;
                freezeDisambiguationChips(bubble);
                invalidateDisambiguationChips(bubble);
                document.querySelectorAll(".disambiguation-chips").forEach((el) => el.remove());
                applyTurnHintFromMeta(meta, breadcrumbs);
                status.setWarning("Revisão");
                streamSources = Array.isArray(meta?.sources) ? meta.sources : [];
                streamSourceDetails = Array.isArray(meta?.source_details)
                    ? meta.source_details
                    : [];
                setBreadcrumbsContent(
                    breadcrumbs,
                    streamSources,
                    sourcesNoteFromMeta(meta),
                    streamSourceDetails,
                    sourceHandlers,
                );
                refreshStreamContextUi(meta, "", breadcrumbs);
                return;
            }

            if (isPostGenerationAdvisory(meta)) {
                turnMode = "markdown";
                applyTurnHintFromMeta(meta, breadcrumbs);
                streamSources = Array.isArray(meta?.sources) ? meta.sources : [];
                streamSourceDetails = Array.isArray(meta?.source_details)
                    ? meta.source_details
                    : [];
                setBreadcrumbsContent(
                    breadcrumbs,
                    streamSources,
                    sourcesNoteFromMeta(meta),
                    streamSourceDetails,
                    sourceHandlers,
                );
                refreshStreamContextUi(meta, "", breadcrumbs);
                return;
            }

            if (isStructuredHardStop(meta)) {
                turnMode = "structured";
                bubble.innerHTML = "";
                statusEl.classList.add("context-search-status--hidden");
                setTurnHintBadge(breadcrumbs, "none");

                if (shouldMountIndexGap(reason, payload, meta)) {
                    mountIndexGapAlert(bubble, payload);
                    indexGapPayload = payload;
                    const lesson = /** @type {{ title?: string }} */ (payload?.expected_lesson);
                    structuredHistoryLabel = `[Index gap] ${lesson?.title || "aula"}`;
                } else if (shouldMountDisambiguationChips(reason, payload, meta)) {
                    mountChipsFromPayload(payload);
                }
                return;
            }

            turnMode = "markdown";
            if (meta && typeof meta.label === "string" && meta.label) {
                thinkingLabel.textContent = `Analisando resumos de ${meta.label}...`;
            }
            streamSources = Array.isArray(meta?.sources) ? meta.sources : [];
            streamSourceDetails = Array.isArray(meta?.source_details)
                ? meta.source_details
                : streamSourceDetails;
            setBreadcrumbsContent(
                breadcrumbs,
                streamSources,
                sourcesNoteFromMeta(meta),
                streamSourceDetails,
                sourceHandlers,
            );
            refreshStreamContextUi(meta, "", breadcrumbs);
            applyTurnHintFromMeta(meta, breadcrumbs);

            const options = disambiguationOptionsFromMeta(meta);
            if (options.length && isDisambiguationGeneration(meta)) {
                pendingMetaOptions = options;
            }
        }

        const result = await chatService.sendStream(text, {
            sessionId,
            history: historyForApi,
            onMeta(meta) {
                applyMetaUi(meta);
            },
            onFirstToken() {
                statusEl.classList.add("context-search-status--hidden");
            },
            onAbort() {
                turnMode = "markdown";
                chipsMounted = false;
                chipsInvalidated = false;
                pendingChipFollowUp = null;
                finalizeTurnFromStream(streamFullText, { aborted: true });
                setTurnHintBadge(breadcrumbs, "none");
                status.setOnline();
            },
            onInactivity() {
                turnMode = "markdown";
                chipsMounted = false;
                pendingChipFollowUp = null;
                finalizeTurnFromStream(streamFullText, { stalled: true });
                setTurnHintBadge(breadcrumbs, "none");
                status.setWarning("Revisão");
            },
            onDelta: (fullText) => {
                streamFullText = fullText;
                if (turnMode === "structured") {
                    console.debug("[ACL] onDelta ignorado (turnMode=structured)", fullText.length);
                    return;
                }
                const parsed = processAmbiguityStreamDisplay(fullText);
                const incremental = parseCompleteOptionsIncremental(fullText);
                renderStreamBubble(parsed, incremental);
                chatView.scrollBottom();
            },
        });

        if (!result.ok || result.isError || !String(result.fullText || "").length) {
            statusEl.classList.add("context-search-status--hidden");
        }

        bubble.classList.remove("cursor-blink");

        if (!result.ok) {
            turnMode = "markdown";
            setTurnHintBadge(breadcrumbs, "none");
            if (streamFullText.trim()) {
                finalizeTurnFromStream(streamFullText, {
                    aborted: Boolean(result.aborted),
                    stalled: Boolean(result.stalled),
                });
                history.push({
                    role: "bot",
                    text: result.message || STREAM_TRUNCATED_AMBIGUITY_MSG,
                });
            } else {
                bubble.classList.add("error");
                bubble.textContent = result.message;
                history.push({ role: "bot", text: result.message });
            }
        } else if (result.isError) {
            bubble.classList.add("error");
            bubble.textContent = result.fullText;
            history.push({ role: "bot", text: result.fullText });
        } else if (turnMode === "structured" || turnMode === "disambiguation_chips") {
            history.push(
                botHistoryEntry(structuredHistoryLabel || "[Resposta estruturada]"),
            );
        } else {
            const finalized = finalizeTurnFromStream(result.fullText || streamFullText);
            refreshStreamContextUi(lastMeta, result.fullText || streamFullText, breadcrumbs);
            setBreadcrumbsContent(
                breadcrumbs,
                streamSources,
                sourcesNoteFromMeta(lastMeta),
                streamSourceDetails,
                sourceHandlers,
            );
            applyTurnHintFromMeta(lastMeta, breadcrumbs);
            const finalText = isPostGenerationOverride(lastMeta)
                ? finalized.displayText
                : [finalized.proseBefore, finalized.proseAfter].filter(Boolean).join("\n\n") ||
                  finalized.displayText ||
                  result.fullText;
            if (!finalized.streamTruncated || chipsMounted) {
                highlightCodeBlocks(bubble);
            }
            history.push(
                botHistoryEntry(
                    chipsMounted
                        ? structuredHistoryLabel || finalText
                        : finalText || STREAM_TRUNCATED_AMBIGUITY_MSG,
                    finalText || result.fullText || "",
                ),
            );
        }

        if (isResetCmd && result.ok) {
            finishConversationReset();
        } else {
            saveHistory(history);
            refreshContextWindowNotice(history.length);
        }

        thinkingGlobe.stop();
        composer.setEnabled(true);
        if (isPostGenerationOverride(lastMeta)) {
            status.setWarning("Revisão");
        } else {
            status.setOnline();
        }
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

    if (composerWrap) {
        createSlashCommandMenu(input, composerWrap);
    }

    sidebar = createConversationSidebar({
        sidebar: sidebarEl,
        listEl: conversationList,
        overlay: sidebarOverlay,
        toggleBtn: sidebarToggle,
        newBtn: sidebarNewBtn,
        getActiveId: () => getActiveConversation().id,
        onSelect: () => reloadConversationView(),
        onNew: () => finishConversationReset(),
    });

    applyDisciplineDeepLink(input, () => refreshSiloUi());

    if (newChatBtn) {
        newChatBtn.addEventListener("click", () => {
            if (sending) return;
            finishConversationReset();
            void sendMessage("/reset");
        });
    }

    input.addEventListener("input", refreshSiloUi);
    refreshSiloUi();
    refreshContextStack();

    chatView.renderSavedHistory(loadHistory());
    refreshContextWindowNotice(loadConversation().turns.length);
    sidebar.render();
    composer.focus();
}
