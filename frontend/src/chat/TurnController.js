import {
    disambiguationOptionsFromMeta,
} from "../acl/parseAmbiguityOptions.js";
import {
    buildDisambiguationFollowUp,
    isDisambiguationGeneration,
    isPostGenerationAdvisory,
    isPostGenerationOverride,
    isStructuredHardStop,
    normalizeHardStopPayload,
    sourcesNoteFromMeta,
    shouldMountDisambiguationChips,
    shouldMountIndexGap,
    resolveTurnHintVariant,
} from "../acl/parseAclMeta.js";
import {
    AMBIGUITY_STREAM_PLACEHOLDER,
    finalizeAmbiguityStreamDisplay,
    mergeDisambiguationOptions,
    parseCompleteOptionsIncremental,
    processAmbiguityStreamDisplay,
    STREAM_TRUNCATED_AMBIGUITY_MSG,
} from "../acl/ambiguityStreamBuffer.js";
import {
    freezeDisambiguationChips,
    invalidateDisambiguationChips,
    syncDisambiguationChips,
} from "../components/DisambiguationChips.js";
import { mountIndexGapAlert } from "../components/IndexGapAlert.js";
import {
    setBreadcrumbsContent,
    setTurnHintBadge,
} from "../components/MessageRow.js";
import { groundingPolicyLabel, reasonLabel } from "../acl/reasonLabel.js";
import { buildTurnMeta } from "./restoreTurn.js";
import { immediateContextLabel } from "../utils/contextLabel.js";
import { highlightCodeBlocks, renderMarkdown } from "../utils/markdown.js";
import { createGlobe } from "../globe.js";
import { markVisitedFromTurn } from "../utils/progress.js";

/**
 * @param {{
 *   chatBox: HTMLElement,
 *   input: HTMLTextAreaElement,
 *   chatView: ReturnType<typeof import('../components/ChatView.js').createChatView>,
 *   streamController: ReturnType<typeof import('./StreamController.js').createStreamController>,
 *   composer: ReturnType<typeof import('../components/Composer.js').createComposer>,
 *   status: ReturnType<typeof import('../components/StatusBadge.js').createStatusBadge>,
 *   metaRenderer: ReturnType<typeof import('./MetaRenderer.js').createMetaRenderer>,
 *   sourceHandlers: { onPinSource?: (d: Record<string, unknown>) => void },
 *   refreshSiloUi: () => void,
 *   getSessionId: () => string,
 *   getHistoryForApi: () => Array<{ role: 'user' | 'assistant', content: string }>,
 *   loadHistory: () => import('../utils/history.js').ConversationTurn[],
 *   saveHistory: (turns: import('../utils/history.js').ConversationTurn[]) => void,
 *   onConversationReset: () => void,
 *   refreshContextWindowNotice: (n: number) => void,
 * }} deps
 */
export function createTurnController(deps) {
    const {
        chatBox,
        input,
        chatView,
        streamController,
        composer,
        status,
        metaRenderer,
        sourceHandlers,
        refreshSiloUi,
        getSessionId,
        getHistoryForApi,
        loadHistory,
        saveHistory,
        onConversationReset,
        refreshContextWindowNotice,
    } = deps;

    const {
        applyTurnHintFromMeta,
        refreshStreamContextUi,
    } = metaRenderer;

    let sending = false;
    /** @type {string | null} */
    let pendingChipFollowUp = null;

    function metaSourcesNote(meta) {
        return sourcesNoteFromMeta(meta);
    }

    function clearStructuredUiArtifacts() {
        document.querySelectorAll(".disambiguation-chips").forEach((el) => el.remove());
        document.querySelectorAll(".index-gap-alert").forEach((el) => el.remove());
    }

    /**
     * @param {string} [overrideText]
     */
    async function send(overrideText) {
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
        composer.setStreaming(true);
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

        /** @type {{ stop?: () => void } | null} */
        let globeRef = thinkingGlobe;

        function disposeThinking() {
            globeRef?.stop?.();
            globeRef = null;
            statusEl.remove();
        }

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

        function botHistoryEntry(entryText, answerText = "") {
            const turnMeta = buildBotTurnMeta(answerText);
            return {
                role: "bot",
                text: entryText,
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
                    void send(followUp);
                },
            };
        }

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
                disposeThinking();
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

        let result;
        try {
            result = await streamController.send(text, getSessionId(), historyForApi, {
                onMeta(meta) {
                    applyMetaUi(meta);
                },
                onFirstToken() {
                    disposeThinking();
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
                const botEntry = botHistoryEntry(
                    chipsMounted
                        ? structuredHistoryLabel || finalText
                        : finalText || STREAM_TRUNCATED_AMBIGUITY_MSG,
                    finalText || result.fullText || "",
                );
                history.push(botEntry);
                markVisitedFromTurn(botEntry, lastMeta);
            }

            if (isResetCmd && result.ok) {
                onConversationReset();
            } else {
                saveHistory(history);
                refreshContextWindowNotice(history.length);
            }

            if (isPostGenerationOverride(lastMeta)) {
                status.setWarning("Revisão");
            } else {
                status.setOnline();
            }
            chatView.scrollBottom();
        } finally {
            disposeThinking();
            composer.setStreaming(false);
            composer.setEnabled(true);
            sending = false;

            const deferred = pendingChipFollowUp;
            pendingChipFollowUp = null;
            if (deferred) {
                void send(deferred);
            } else {
                composer.focus();
            }
        }
    }

    function queueFollowUp(text) {
        if (sending) {
            pendingChipFollowUp = text;
            return true;
        }
        return false;
    }

    function abortStream() {
        if (!sending) return;
        streamController.abort();
    }

    async function regenerateLast() {
        if (sending) return;
        const history = loadHistory();
        let lastUserIdx = -1;
        for (let i = history.length - 1; i >= 0; i -= 1) {
            if (history[i].role === "user") {
                lastUserIdx = i;
                break;
            }
        }
        if (lastUserIdx === -1) return;

        const userText = history[lastUserIdx].text;
        const trimmed = history.slice(0, lastUserIdx);
        saveHistory(trimmed);
        refreshContextWindowNotice(trimmed.length);

        const rows = chatBox.querySelectorAll(".message-row");
        for (let i = rows.length - 1; i >= lastUserIdx; i -= 1) {
            rows[i]?.remove();
        }

        await send(userText);
    }

    return {
        send,
        isSending: () => sending,
        queueFollowUp,
        abortStream,
        regenerateLast,
    };
}
