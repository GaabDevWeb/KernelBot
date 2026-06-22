import { fmt } from "../utils/time.js";
import { parseSourceParts } from "../utils/formatSource.js";

const MAX_VISIBLE_SOURCES = 3;

/**
 * @param {HTMLElement} breadcrumbsEl
 * @param {string[] | undefined} sources
 */
const HINT_CLASS = "message-hint-badge";
const HINT_VARIANTS = {
    disambiguation: "message-hint-badge--disambiguation",
    misalignment: "message-hint-badge--misalignment",
    advisory: "message-hint-badge--advisory",
    scope: "message-hint-badge--scope",
};

const CONTEXT_BADGE_CLASS = "message-context-badge";
const SOURCES_NOTE_CLASS = "message-sources-note";

/**
 * Badges de reason / grounding_policy ao lado dos breadcrumbs.
 * @param {HTMLElement | null | undefined} breadcrumbsEl
 * @param {{ reason?: string, groundingPolicy?: string, pedagogy?: boolean }} opts
 */
export function setContextBadges(breadcrumbsEl, opts) {
    if (!breadcrumbsEl) return;
    breadcrumbsEl.querySelectorAll(`.${CONTEXT_BADGE_CLASS}`).forEach((el) => el.remove());

    const items = [];
    if (opts.groundingPolicy) {
        items.push({ text: opts.groundingPolicy, variant: "course" });
    }
    if (opts.reason) {
        items.push({ text: opts.reason, variant: "weak" });
    }
    if (opts.pedagogy) {
        items.push({ text: "Complemento pedagógico", variant: "pedagogy" });
    }
    if (!items.length) {
        if (!breadcrumbsEl.childElementCount) breadcrumbsEl.hidden = true;
        return;
    }

    breadcrumbsEl.hidden = false;
    const wrap = document.createElement("div");
    wrap.className = "message-context-badges";
    for (const item of items) {
        const badge = document.createElement("span");
        badge.className = `${CONTEXT_BADGE_CLASS} message-context-badge--${item.variant}`;
        badge.textContent = item.text;
        wrap.appendChild(badge);
    }
    breadcrumbsEl.prepend(wrap);
}

/**
 * Badge informativo reactivo (desambiguação / override / advisory pós-geração).
 * @param {HTMLElement | null | undefined} breadcrumbsEl
 * @param {"none" | "disambiguation" | "misalignment" | "advisory" | "scope"} variant
 * @param {string} [hintText] — obrigatório para variant `scope` (meta.scope_hint)
 */
export function setTurnHintBadge(breadcrumbsEl, variant, hintText) {
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
    } else if (variant === "advisory") {
        hint.classList.add(HINT_VARIANTS.advisory);
        hint.textContent =
            "A checagem automática sugere rever as fontes — a resposta acima foi mantida.";
    } else if (variant === "scope") {
        hint.classList.add(HINT_VARIANTS.scope);
        const t = (hintText || "").trim();
        hint.textContent =
            t ||
            "O tema fixado pode não coincidir com a pergunta — use um comando de disciplina ou /reset.";
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

/**
 * @param {HTMLElement | null | undefined} breadcrumbsEl
 * @param {string[] | undefined} sources
 * @param {string | null | undefined} [sourcesNote]
 */
export function setBreadcrumbsContent(breadcrumbsEl, sources, sourcesNote) {
    if (!breadcrumbsEl) return;
    const noteText = (sourcesNote || "").trim();
    const list = Array.isArray(sources) ? sources.filter(Boolean) : [];

    if (!list.length && !noteText) {
        breadcrumbsEl.hidden = true;
        breadcrumbsEl.replaceChildren();
        return;
    }

    breadcrumbsEl.hidden = false;
    breadcrumbsEl.replaceChildren();

    if (list.length) {
        const block = document.createElement("div");
        block.className = "message-sources";

        const heading = document.createElement("p");
        heading.className = "message-sources__heading";
        heading.textContent =
            list.length === 1 ? "Fonte consultada" : `Fontes consultadas (${list.length})`;
        block.appendChild(heading);

        const ul = document.createElement("ul");
        ul.className = "message-sources__list";

        const visible = list.slice(0, MAX_VISIBLE_SOURCES);
        const hidden = list.slice(MAX_VISIBLE_SOURCES);

        for (const raw of visible) {
            ul.appendChild(buildSourceCard(raw));
        }

        if (hidden.length) {
            const extraWrap = document.createElement("li");
            extraWrap.className = "message-sources__extra";
            extraWrap.hidden = true;
            const extraUl = document.createElement("ul");
            extraUl.className = "message-sources__list message-sources__list--extra";
            for (const raw of hidden) {
                extraUl.appendChild(buildSourceCard(raw));
            }
            extraWrap.appendChild(extraUl);
            ul.appendChild(extraWrap);

            const toggle = document.createElement("button");
            toggle.type = "button";
            toggle.className = "message-sources__toggle";
            toggle.textContent = `Ver mais ${hidden.length} fonte${hidden.length === 1 ? "" : "s"}`;
            toggle.addEventListener("click", () => {
                const open = !extraWrap.hidden;
                extraWrap.hidden = open;
                toggle.textContent = open
                    ? `Ver mais ${hidden.length} fonte${hidden.length === 1 ? "" : "s"}`
                    : "Ver menos";
                toggle.setAttribute("aria-expanded", open ? "false" : "true");
            });
            block.appendChild(ul);
            block.appendChild(toggle);
        } else {
            block.appendChild(ul);
        }

        breadcrumbsEl.appendChild(block);
    }

    if (noteText) {
        const note = document.createElement("div");
        note.className = SOURCES_NOTE_CLASS;
        note.textContent = noteText;
        breadcrumbsEl.appendChild(note);
    }
}

/**
 * @param {string} raw
 * @returns {HTMLLIElement}
 */
function buildSourceCard(raw) {
    const parts = parseSourceParts(raw);
    const li = document.createElement("li");
    li.className = "source-card";

    const body = document.createElement("div");
    body.className = "source-card__body";

    if (parts?.discipline) {
        const disc = document.createElement("span");
        disc.className = "source-card__discipline";
        disc.textContent = parts.discipline;
        body.appendChild(disc);
    }

    const lesson = document.createElement("span");
    lesson.className = "source-card__lesson";
    lesson.textContent = parts?.lesson || parts?.raw || raw;
    body.appendChild(lesson);

    li.append(body);
    return li;
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
    meta.textContent = role === "user" ? `Você · ${fmt(now)}` : `Kernel · ${fmt(now)}`;

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
    meta.textContent = `Kernel · ${fmt(new Date())}`;

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
