import { fmt } from "../utils/time.js";
import { parseSourceParts } from "../utils/formatSource.js";

const MAX_VISIBLE_SOURCES = 3;

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
 * @param {string[] | undefined} sources
 * @param {Array<Record<string, unknown>> | undefined} sourceDetails
 * @returns {Array<Record<string, unknown>>}
 */
function normalizeSourceDetails(sources, sourceDetails) {
    if (Array.isArray(sourceDetails) && sourceDetails.length) {
        return sourceDetails;
    }
    return (sources || []).map((raw) => {
        const p = parseSourceParts(raw);
        return {
            source: raw,
            discipline_label: p?.discipline || "",
            lesson_title: p?.lesson || raw,
            module: null,
            excerpt: "",
        };
    });
}

/**
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
 * @param {HTMLElement | null | undefined} breadcrumbsEl
 * @param {"none" | "disambiguation" | "misalignment" | "advisory" | "scope"} variant
 * @param {string} [hintText]
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
 * @param {Array<Record<string, unknown>> | undefined} [sourceDetails]
 * @param {{ onPinSource?: (detail: Record<string, unknown>) => void }} [handlers]
 */
export function setBreadcrumbsContent(
    breadcrumbsEl,
    sources,
    sourcesNote,
    sourceDetails,
    handlers = {},
) {
    if (!breadcrumbsEl) return;
    const noteText = (sourcesNote || "").trim();
    const details = normalizeSourceDetails(sources, sourceDetails);

    if (!details.length && !noteText) {
        breadcrumbsEl.hidden = true;
        breadcrumbsEl.replaceChildren();
        return;
    }

    breadcrumbsEl.hidden = false;
    breadcrumbsEl.replaceChildren();

    if (details.length) {
        const block = document.createElement("div");
        block.className = "message-sources";

        const heading = document.createElement("p");
        heading.className = "message-sources__heading";
        heading.textContent =
            details.length === 1
                ? "Material usado nesta resposta"
                : `Materiais usados nesta resposta (${details.length})`;
        block.appendChild(heading);

        const ul = document.createElement("ul");
        ul.className = "message-sources__list";

        const visible = details.slice(0, MAX_VISIBLE_SOURCES);
        const hidden = details.slice(MAX_VISIBLE_SOURCES);

        for (const detail of visible) {
            ul.appendChild(buildRichSourceCard(detail, handlers));
        }

        if (hidden.length) {
            const extraWrap = document.createElement("li");
            extraWrap.className = "message-sources__extra";
            extraWrap.hidden = true;
            const extraUl = document.createElement("ul");
            extraUl.className = "message-sources__list message-sources__list--extra";
            for (const detail of hidden) {
                extraUl.appendChild(buildRichSourceCard(detail, handlers));
            }
            extraWrap.appendChild(extraUl);
            ul.appendChild(extraWrap);

            const toggle = document.createElement("button");
            toggle.type = "button";
            toggle.className = "message-sources__toggle";
            toggle.textContent = `Ver mais ${hidden.length} fonte${hidden.length === 1 ? "" : "s"}`;
            toggle.setAttribute("aria-expanded", "false");
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
 * @param {Record<string, unknown>} detail
 * @param {{ onPinSource?: (detail: Record<string, unknown>) => void }} handlers
 * @returns {HTMLLIElement}
 */
function buildRichSourceCard(detail, handlers) {
    const li = document.createElement("li");
    li.className = "source-card source-card--rich";

    const title = document.createElement("p");
    title.className = "source-card__title";
    const lessonTitle = String(detail.lesson_title || "Aula").trim();
    title.textContent = `Aula: ${lessonTitle}`;

    const metaRow = document.createElement("div");
    metaRow.className = "source-card__meta-row";

    const discLabel = String(detail.discipline_label || "").trim();
    if (discLabel) {
        const disc = document.createElement("span");
        disc.className = "source-card__meta-item";
        disc.innerHTML = `<span class="source-card__meta-k">Disciplina</span> ${discLabel}`;
        metaRow.appendChild(disc);
    }

    const module = detail.module ? String(detail.module).trim() : "";
    if (module) {
        const mod = document.createElement("span");
        mod.className = "source-card__meta-item";
        mod.innerHTML = `<span class="source-card__meta-k">Sequência</span> ${module}`;
        metaRow.appendChild(mod);
    }

    li.appendChild(title);
    if (metaRow.childElementCount) li.appendChild(metaRow);

    const excerpt = String(detail.excerpt || "").trim();
    if (excerpt) {
        const exLabel = document.createElement("p");
        exLabel.className = "source-card__excerpt-label";
        exLabel.textContent = "Trecho encontrado";

        const ex = document.createElement("blockquote");
        ex.className = "source-card__excerpt";
        ex.textContent = excerpt;

        li.appendChild(exLabel);
        li.appendChild(ex);
    }

    const actions = document.createElement("div");
    actions.className = "source-card__actions";

    if (excerpt) {
        const viewBtn = document.createElement("button");
        viewBtn.type = "button";
        viewBtn.className = "source-card__action source-card__action--secondary";
        viewBtn.textContent = "Ver trecho";
        viewBtn.setAttribute("aria-expanded", "false");
        const excerptEl = li.querySelector(".source-card__excerpt");
        viewBtn.addEventListener("click", () => {
            if (!excerptEl) return;
            const expanded = excerptEl.classList.toggle("source-card__excerpt--expanded");
            viewBtn.textContent = expanded ? "Recolher" : "Ver trecho";
            viewBtn.setAttribute("aria-expanded", expanded ? "true" : "false");
        });
        actions.appendChild(viewBtn);
    }

    if (handlers.onPinSource && (detail.slug || detail.discipline)) {
        const pinBtn = document.createElement("button");
        pinBtn.type = "button";
        pinBtn.className = "source-card__action source-card__action--primary";
        pinBtn.textContent = "Fixar contexto";
        pinBtn.addEventListener("click", () => handlers.onPinSource?.(detail));
        actions.appendChild(pinBtn);
    }

    if (actions.childElementCount) li.appendChild(actions);
    return li;
}

/**
 * @param {HTMLElement} chatBox
 * @param {{ role: 'user'|'bot', text: string, isError?: boolean, sources?: string[], sourceDetails?: Array<Record<string, unknown>>, renderMarkdown: (t: string) => string, animated?: boolean, scrollBottom: () => void, sourceHandlers?: { onPinSource?: (d: Record<string, unknown>) => void } }} opts
 */
export function appendMessageRow(chatBox, opts) {
    const {
        role,
        text,
        isError = false,
        sources,
        sourceDetails,
        renderMarkdown,
        animated = true,
        scrollBottom,
        sourceHandlers,
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
        setBreadcrumbsContent(breadcrumbs, sources, undefined, sourceDetails, sourceHandlers);
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
