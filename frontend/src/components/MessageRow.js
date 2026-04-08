import { fmt } from "../utils/time.js";

const MAX_BREADCRUMB_LINES = 5;

/**
 * @param {HTMLElement} breadcrumbsEl
 * @param {string[] | undefined} sources
 */
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

    row.appendChild(meta);
    row.appendChild(breadcrumbs);
    row.appendChild(bubble);
    chatBox.appendChild(row);
    scrollBottom();
    return { row, bubble, breadcrumbs };
}
