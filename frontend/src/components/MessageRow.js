import { fmt } from "../utils/time.js";

const MAX_BREADCRUMB_LINES = 5;

/**
 * @param {HTMLElement} breadcrumbsEl
 * @param {string[] | undefined} sources
 */
const HINT_CLASS = "message-hint-badge";
const HINT_VARIANTS = {
    disambiguation: "message-hint-badge--disambiguation",
    misalignment: "message-hint-badge--misalignment",
};

/**
 * Badge informativo reactivo (desambiguação / override pós-geração).
 * @param {HTMLElement | null | undefined} breadcrumbsEl
 * @param {"none" | "disambiguation" | "misalignment"} variant
 */
export function setTurnHintBadge(breadcrumbsEl, variant) {
    if (!breadcrumbsEl) return;
    const existing = breadcrumbsEl.querySelector(`.${HINT_CLASS}`);
    if (variant === "none") {
        existing?.remove();
        if (!breadcrumbsEl.childElementCount) breadcrumbsEl.hidden = true;
        return;
    }
    breadcrumbsEl.hidden = false;
    const hint = existing ?? document.createElement("div");
    hint.className = HINT_CLASS;
    Object.values(HINT_VARIANTS).forEach((c) => hint.classList.remove(c));
    if (variant === "misalignment") {
        hint.classList.add(HINT_VARIANTS.misalignment);
        hint.textContent =
            "Resposta revista — o conteúdo gerado não alinhou com as fontes recuperadas.";
    } else {
        hint.classList.add(HINT_VARIANTS.disambiguation);
        hint.textContent = "Várias fontes próximas — escolha uma aula abaixo ou continue no texto.";
    }
    if (!existing) breadcrumbsEl.prepend(hint);
}

/** @deprecated Use setTurnHintBadge(breadcrumbsEl, show ? "disambiguation" : "none") */
export function setDisambiguationHint(breadcrumbsEl, show) {
    setTurnHintBadge(breadcrumbsEl, show ? "disambiguation" : "none");
}

export function setBreadcrumbsContent(breadcrumbsEl, sources) {
    if (!breadcrumbsEl) return;
    if (!sources?.length) {
        breadcrumbsEl.hidden = true;
        breadcrumbsEl.replaceChildren();
        return;
    }
    breadcrumbsEl.hidden = false;
    breadcrumbsEl.replaceChildren();
    const slice = sources.slice(0, MAX_BREADCRUMB_LINES);
    for (const path of slice) {
        const line = document.createElement("div");
        line.className = "message-breadcrumb-line";
        line.textContent = path.split("/").join(" > ");
        breadcrumbsEl.appendChild(line);
    }
    const extra = sources.length - slice.length;
    if (extra > 0) {
        const more = document.createElement("div");
        more.className = "message-breadcrumb-more";
        more.textContent = `+${extra} ficheiro${extra === 1 ? "" : "s"}`;
        breadcrumbsEl.appendChild(more);
    }
}

/**
 * @param {HTMLElement} chatBox
 * @param {{ role: 'user'|'bot', text: string, isError?: boolean, sources?: string[], renderMarkdown: (t: string) => string, animated?: boolean, scrollBottom: () => void }} opts
 * @returns {HTMLElement} bubble element
 */
export function appendMessageRow(chatBox, opts) {
    const {
        role,
        text,
        isError = false,
        sources,
        renderMarkdown,
        animated = true,
        scrollBottom,
    } = opts;

    const row = document.createElement("div");
    row.classList.add("message-row", role);
    if (animated) row.style.animationDelay = "0ms";

    const meta = document.createElement("div");
    meta.className = "message-meta";
    const now = new Date();
    meta.textContent = role === "user" ? `Você · ${fmt(now)}` : `ACL · ${fmt(now)}`;

    const breadcrumbs = document.createElement("div");
    breadcrumbs.className = "message-breadcrumbs";
    if (role === "bot" && !isError) {
        setBreadcrumbsContent(breadcrumbs, sources);
    } else {
        breadcrumbs.hidden = true;
    }

    const bubble = document.createElement("div");
    bubble.classList.add("message", role);
    if (isError) bubble.classList.add("error");

    if (role === "bot" && !isError) {
        bubble.innerHTML = renderMarkdown(text);
    } else {
        bubble.textContent = text;
    }

    row.appendChild(meta);
    if (role === "bot") row.appendChild(breadcrumbs);
    row.appendChild(bubble);
    chatBox.appendChild(row);
    scrollBottom();
    return bubble;
}

/**
 * @param {HTMLElement} chatBox
 * @param {() => void} scrollBottom
 */
export function createStreamingBotRow(chatBox, scrollBottom) {
    const row = document.createElement("div");
    row.classList.add("message-row", "bot");

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = `ACL · ${fmt(new Date())}`;

    const breadcrumbs = document.createElement("div");
    breadcrumbs.className = "message-breadcrumbs";
    breadcrumbs.hidden = true;

    const bubble = document.createElement("div");
    bubble.classList.add("message", "bot", "cursor-blink");

    const prose = document.createElement("div");
    prose.className = "stream-prose";
    const ambiguitySlot = document.createElement("div");
    ambiguitySlot.className = "stream-ambiguity-slot";
    const postAmbiguity = document.createElement("div");
    postAmbiguity.className = "stream-post-ambiguity";
    bubble.appendChild(prose);
    bubble.appendChild(ambiguitySlot);
    bubble.appendChild(postAmbiguity);

    row.appendChild(meta);
    row.appendChild(breadcrumbs);
    row.appendChild(bubble);
    chatBox.appendChild(row);
    scrollBottom();
    return { row, bubble, breadcrumbs, prose, ambiguitySlot, postAmbiguity };
}
