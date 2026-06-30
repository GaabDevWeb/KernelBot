import { syncDisambiguationChips } from "../components/DisambiguationChips.js";
import { mountIndexGapAlert } from "../components/IndexGapAlert.js";
import {
    setBreadcrumbsContent,
    setContextBadges,
    setTurnHintBadge,
    mountMessageToolbar,
} from "../components/MessageRow.js";
import { fmt } from "../utils/time.js";
import { stripDisciplinePrefixForDisplay } from "../config/disciplines.js";
import { buildIssMarkdownContext } from "../utils/issLinks.js";

/**
 * @typedef {Object} TurnMeta
 * @property {'markdown' | 'structured' | 'disambiguation_chips'} turnType
 * @property {string} [reason]
 * @property {string} [discipline]
 * @property {string} [groundingPolicy]
 * @property {{ variant: string, text?: string }} [hint]
 * @property {boolean} [pedagogy]
 * @property {string} [sourcesNote]
 * @property {Record<string, unknown>} [indexGap]
 * @property {{ candidates: Array<{title: string, discipline: string, slug: string}>, frozen: boolean, invalidated: boolean, rescued: boolean }} [disambiguation]
 * @property {Record<string, unknown>} [aclSnapshot]
 */

/**
 * @param {Record<string, unknown> | null | undefined} meta
 * @param {string} answerText
 * @param {boolean} isOverride
 */
function pedagogyFromText(meta, answerText, isOverride) {
    if (isOverride) return false;
    return /extens[aã]o pedag[oó]gica\s*\(fora do material indexado\)/i.test(answerText);
}

/**
 * Monta turnMeta serializável a partir do estado do turno.
 * @param {{
 *   turnMode: string,
 *   lastMeta: Record<string, unknown> | null,
 *   structuredHistoryLabel?: string,
 *   chipsMounted?: boolean,
 *   chipsInvalidated?: boolean,
 *   turnRescuedFromStream?: boolean,
 *   disambiguationCandidates?: Array<{ title: string, discipline: string, slug: string }>,
 *   indexGapPayload?: Record<string, unknown> | null,
 *   answerText?: string,
 *   groundingPolicyLabel?: (p: string) => string,
 *   reasonLabel?: (r: string) => string,
 *   sourcesNoteFromMeta?: (m: Record<string, unknown> | null) => string | null,
 *   resolveTurnHintVariant?: (m: Record<string, unknown> | null) => { variant: string, text?: string | null },
 *   isPostGenerationOverride?: (m: Record<string, unknown> | null) => boolean,
 * }} ctx
 * @returns {TurnMeta | undefined}
 */
export function buildTurnMeta(ctx) {
    const {
        turnMode,
        lastMeta,
        chipsMounted = false,
        chipsInvalidated = false,
        turnRescuedFromStream = false,
        disambiguationCandidates = [],
        indexGapPayload = null,
        answerText = "",
        groundingPolicyLabel: gpLabel,
        reasonLabel: rLabel,
        sourcesNoteFromMeta: snFromMeta,
        resolveTurnHintVariant: resolveHint,
        isPostGenerationOverride: isOverrideFn,
    } = ctx;

    if (turnMode === "structured" && indexGapPayload) {
        const lesson = /** @type {{ title?: string, discipline?: string, slug?: string }} */ (
            indexGapPayload.expected_lesson
        );
        return {
            turnType: "structured",
            reason: String(lastMeta?.reason || "index_gap"),
            indexGap: {
                expected_lesson: lesson || {},
                suggested_candidates: indexGapPayload.suggested_candidates || [],
            },
            aclSnapshot: snapshotAcl(lastMeta),
        };
    }

    if (turnMode === "disambiguation_chips" || (turnMode === "structured" && chipsMounted)) {
        const candidates =
            disambiguationCandidates.length > 0
                ? disambiguationCandidates
                : extractCandidatesFromPayload(indexGapPayload);
        return {
            turnType: "disambiguation_chips",
            reason: String(lastMeta?.reason || "ambiguous_retrieval"),
            discipline: typeof lastMeta?.label === "string" ? lastMeta.label : undefined,
            hint: resolveHint?.(lastMeta) ?? { variant: "disambiguation" },
            disambiguation: {
                candidates,
                frozen: false,
                invalidated: chipsInvalidated,
                rescued: turnRescuedFromStream,
            },
            aclSnapshot: snapshotAcl(lastMeta),
        };
    }

    if (!lastMeta && turnMode === "markdown") return undefined;

    const isOverride = isOverrideFn?.(lastMeta ?? null) ?? false;
    const hint = resolveHint?.(lastMeta ?? null);

    return {
        turnType: "markdown",
        reason: rLabel?.(String(lastMeta?.reason || "")) || undefined,
        discipline: typeof lastMeta?.label === "string" ? lastMeta.label : undefined,
        groundingPolicy: gpLabel?.(String(lastMeta?.grounding_policy || "")) || undefined,
        hint: hint && hint.variant !== "none" ? hint : undefined,
        pedagogy: pedagogyFromText(lastMeta, answerText, isOverride),
        sourcesNote: snFromMeta?.(lastMeta ?? null) || undefined,
        aclSnapshot: snapshotAcl(lastMeta),
    };
}

/**
 * @param {Record<string, unknown> | null | undefined} meta
 */
function snapshotAcl(meta) {
    if (!meta) return undefined;
    const keys = [
        "reason",
        "label",
        "grounding_policy",
        "allow_generation",
        "pinned_active",
        "pinned_display",
        "scope_hint",
        "sources_note",
    ];
    /** @type {Record<string, unknown>} */
    const out = {};
    for (const k of keys) {
        if (meta[k] !== undefined) out[k] = meta[k];
    }
    return Object.keys(out).length ? out : undefined;
}

/**
 * Restaura pin badge a partir do último snapshot ACL persistido.
 * @param {Array<{ role?: string, turnMeta?: { aclSnapshot?: Record<string, unknown> } }>} turns
 * @param {(meta: Record<string, unknown>) => void} refreshPinBadge
 * @param {() => void} hidePinBadge
 */
export function restoreSessionPinFromHistory(turns, refreshPinBadge, hidePinBadge) {
    if (!Array.isArray(turns) || !turns.length) {
        hidePinBadge();
        return;
    }
    for (let i = turns.length - 1; i >= 0; i -= 1) {
        const snap = turns[i]?.turnMeta?.aclSnapshot;
        if (snap?.pinned_active) {
            refreshPinBadge(snap);
            return;
        }
    }
    hidePinBadge();
}

/**
 * @param {Record<string, unknown> | null | undefined} payload
 */
function extractCandidatesFromPayload(payload) {
    if (!payload || !Array.isArray(payload.suggested_candidates)) return [];
    return payload.suggested_candidates
        .map((c) => {
            if (!c || typeof c !== "object") return null;
            return {
                title: String(c.title || c.slug || "Aula"),
                discipline: String(c.discipline || ""),
                slug: String(c.slug || ""),
            };
        })
        .filter(Boolean);
}

/**
 * Restaura UI rica de um turno bot salvo.
 * @param {{
 *   row: HTMLElement,
 *   bubble: HTMLElement,
 *   breadcrumbs: HTMLElement,
 *   turn: { text: string, sources?: string[], sourceDetails?: Array<Record<string, unknown>>, turnMeta?: TurnMeta },
 *   renderMarkdown: (t: string) => string,
 *   sourceHandlers?: { onPinSource?: (d: Record<string, unknown>) => void },
 *   chipHandlers?: { onSelect: (c: { title?: string, discipline?: string, slug?: string }) => void },
 * }} opts
 */
export function restoreBotTurn({
    row,
    bubble,
    breadcrumbs,
    turn,
    renderMarkdown,
    sourceHandlers,
    chipHandlers,
}) {
    const tm = turn.turnMeta;
    const sourcesNote = tm?.sourcesNote;

    setBreadcrumbsContent(
        breadcrumbs,
        turn.sources,
        sourcesNote,
        turn.sourceDetails,
        sourceHandlers,
    );

    const mdContext = buildIssMarkdownContext({ sourceDetails: turn.sourceDetails });

    if (!tm) {
        if (turn.text && !turn.text.startsWith("[")) {
            bubble.innerHTML = renderMarkdown(turn.text, mdContext);
        } else {
            bubble.textContent = turn.text;
        }
        return;
    }

    if (tm.groundingPolicy || tm.reason || tm.pedagogy) {
        setContextBadges(breadcrumbs, {
            groundingPolicy: tm.groundingPolicy,
            reason: tm.reason,
            pedagogy: tm.pedagogy,
        });
    }

    if (tm.hint && tm.hint.variant !== "none") {
        setTurnHintBadge(
            breadcrumbs,
            /** @type {'disambiguation' | 'misalignment' | 'advisory' | 'scope'} */ (tm.hint.variant),
            tm.hint.text,
        );
    }

    if (tm.turnType === "structured" && tm.indexGap) {
        bubble.replaceChildren();
        mountIndexGapAlert(bubble, tm.indexGap);
        return;
    }

    if (tm.turnType === "disambiguation_chips" && tm.disambiguation?.candidates?.length) {
        bubble.replaceChildren();
        const wrap = syncDisambiguationChips(bubble, tm.disambiguation.candidates, {
            onSelect: chipHandlers?.onSelect ?? (() => {}),
            rescued: tm.disambiguation.rescued,
        });
        if (wrap && tm.disambiguation.frozen) {
            wrap.classList.add("disambiguation-chips--frozen");
        }
        if (wrap && tm.disambiguation.invalidated) {
            wrap.classList.add("disambiguation-chips--invalidated");
        }
        return;
    }

    if (turn.text && !turn.text.startsWith("[")) {
        bubble.innerHTML = renderMarkdown(turn.text, mdContext);
    } else {
        bubble.textContent = turn.text;
    }
}

/**
 * @param {HTMLElement} chatBox
 * @param {{
 *   role: 'user'|'bot',
 *   text: string,
 *   isError?: boolean,
 *   sources?: string[],
 *   sourceDetails?: Array<Record<string, unknown>>,
 *   turnMeta?: TurnMeta,
 *   renderMarkdown: (t: string) => string,
 *   animated?: boolean,
 *   scrollBottom: () => void,
 *   sourceHandlers?: { onPinSource?: (d: Record<string, unknown>) => void },
 *   chipHandlers?: { onSelect: (c: { title?: string, discipline?: string, slug?: string }) => void },
 *   toolbarHandlers?: { onRegenerate?: () => void, isLastBot?: boolean },
 * }} opts
 */
export function appendMessageRowWithMeta(chatBox, opts) {
    const {
        role,
        text,
        isError = false,
        sources,
        sourceDetails,
        turnMeta,
        renderMarkdown,
        animated = true,
        scrollBottom,
        sourceHandlers,
        chipHandlers,
        toolbarHandlers,
    } = opts;

    const row = document.createElement("div");
    row.classList.add("message-row", role);
    if (animated) row.style.animationDelay = "0ms";

    const meta = document.createElement("div");
    meta.className = "message-meta";
    const now = new Date();
    meta.textContent = role === "user" ? `Você · ${fmt(now)}` : `Kernel · ${fmt(now)}`;

    const breadcrumbs = document.createElement("div");
    breadcrumbs.className = "message-breadcrumbs";
    breadcrumbs.hidden = true;

    const bubble = document.createElement("div");
    bubble.classList.add("message", role);
    if (isError) bubble.classList.add("error");

    row.appendChild(meta);
    row.appendChild(bubble);
    if (role === "bot") row.appendChild(breadcrumbs);
    chatBox.appendChild(row);

    if (role === "user" || isError) {
        bubble.textContent =
            role === "user" && !isError
                ? stripDisciplinePrefixForDisplay(text)
                : text;
    } else if (turnMeta || sources?.length || sourceDetails?.length) {
        restoreBotTurn({
            row,
            bubble,
            breadcrumbs,
            turn: { text, sources, sourceDetails, turnMeta },
            renderMarkdown,
            sourceHandlers,
            chipHandlers,
        });
    } else {
        bubble.innerHTML = renderMarkdown(
            text,
            buildIssMarkdownContext({ sourceDetails }),
        );
    }

    if (!isError) {
        mountMessageToolbar(row, role, text, {
            onRegenerate: toolbarHandlers?.onRegenerate,
            showRegenerate: role === "bot" && Boolean(toolbarHandlers?.isLastBot),
        });
    }

    scrollBottom();
    return bubble;
}
