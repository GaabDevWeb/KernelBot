import {
    resolveTurnHintVariant,
    scopeHintFromMeta,
    sourcesNoteFromMeta,
    isPostGenerationOverride,
} from "../acl/parseAclMeta.js";
import { groundingPolicyLabel, reasonLabel } from "../acl/reasonLabel.js";
import { setContextBadges, setTurnHintBadge } from "../components/MessageRow.js";

/**
 * @param {{ pinBadge: HTMLElement | null, contextStack: HTMLElement | null, refreshContextStack: () => void }} deps
 */
export function createMetaRenderer({ pinBadge, contextStack, refreshContextStack }) {
    function refreshPinBadge(meta) {
        if (!pinBadge) return;
        const labelEl = pinBadge.querySelector(".context-pin-label");
        const active = Boolean(meta?.pinned_active);
        const label = typeof meta?.pinned_display === "string" ? meta.pinned_display.trim() : "";
        if (active && label) {
            pinBadge.hidden = false;
            const continuing = meta?.pin_chunks_used === true;
            let text = continuing ? `Continuando: ${label}` : `aula: "${label}"`;
            const cmd =
                typeof meta?.suggested_scope_command === "string"
                    ? meta.suggested_scope_command.trim()
                    : "";
            if (continuing && cmd) text += ` — experimente ${cmd}`;
            if (labelEl) labelEl.textContent = text;
            const hint = scopeHintFromMeta(meta);
            if (hint) pinBadge.title = hint;
            else pinBadge.removeAttribute("title");
        } else {
            pinBadge.hidden = true;
            if (labelEl) labelEl.textContent = "";
            pinBadge.removeAttribute("title");
        }
        refreshContextStack();
    }

    function hidePinBadge() {
        if (!pinBadge) return;
        const labelEl = pinBadge.querySelector(".context-pin-label");
        pinBadge.hidden = true;
        if (labelEl) labelEl.textContent = "";
        pinBadge.removeAttribute("title");
        refreshContextStack();
    }

    function applyTurnHintFromMeta(meta, breadcrumbsEl) {
        const { variant, text } = resolveTurnHintVariant(meta);
        setTurnHintBadge(breadcrumbsEl, variant, text ?? undefined);
    }

    function refreshStreamContextUi(meta, answerText = "", breadcrumbsEl) {
        refreshPinBadge(meta);
        if (!meta || !breadcrumbsEl) return;
        const pedagogy = /extens[aã]o pedag[oó]gica\s*\(fora do material indexado\)/i.test(
            answerText,
        );
        setContextBadges(breadcrumbsEl, {
            groundingPolicy: groundingPolicyLabel(String(meta.grounding_policy || "")),
            reason: reasonLabel(String(meta.reason || "")),
            pedagogy: pedagogy && !isPostGenerationOverride(meta),
        });
    }

    return {
        refreshPinBadge,
        hidePinBadge,
        applyTurnHintFromMeta,
        refreshStreamContextUi,
        sourcesNoteFromMeta,
    };
}

/**
 * @param {{ refresh: (n?: number) => void }} notice
 */
export function createHistoryController(notice) {
    return {
        refreshContextWindow(turnCount) {
            notice.refresh(turnCount);
        },
    };
}
