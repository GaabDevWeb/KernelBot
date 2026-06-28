import { commandForDiscipline, labelForDiscipline } from "../config/disciplines.js";
import { getProgress, suggestNext } from "../utils/progress.js";

/**
 * @param {{
 *   input: HTMLTextAreaElement,
 *   refreshSiloUi: () => void,
 *   getDisciplineId: () => string | null,
 *   scopeBtn?: HTMLElement | null,
 *   siloPill?: HTMLElement | null,
 * }} opts
 */
export function createDisciplinePanel(opts) {
    const { input, refreshSiloUi, getDisciplineId, scopeBtn, siloPill } = opts;

    /** @type {HTMLElement | null} */
    let panel = null;
    /** @type {HTMLElement | null} */
    let overlay = null;
    /** @type {{ discipline: string, label: string, lessons: Array<{ slug: string, title: string, order?: number }> } | null} */
    let cachedCurriculum = null;
    let cachedDisciplineId = null;

    function ensureDom() {
        if (panel) return;
        overlay = document.createElement("div");
        overlay.className = "discipline-panel-overlay";
        overlay.hidden = true;
        overlay.addEventListener("click", close);

        panel = document.createElement("aside");
        panel.className = "discipline-panel";
        panel.hidden = true;
        panel.setAttribute("aria-label", "Mapa da disciplina");

        const head = document.createElement("div");
        head.className = "discipline-panel__head";
        const title = document.createElement("h2");
        title.className = "discipline-panel__title";
        title.id = "discipline-panel-title";
        const closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.className = "discipline-panel__close";
        closeBtn.setAttribute("aria-label", "Fechar mapa");
        closeBtn.textContent = "Fechar";
        closeBtn.addEventListener("click", close);
        head.append(title, closeBtn);

        const body = document.createElement("div");
        body.className = "discipline-panel__body";
        body.id = "discipline-panel-body";

        panel.append(head, body);
        document.body.append(overlay, panel);
    }

    function close() {
        if (panel) panel.hidden = true;
        if (overlay) overlay.hidden = true;
    }

    function open() {
        ensureDom();
        if (panel) panel.hidden = false;
        if (overlay) overlay.hidden = false;
    }

    /**
     * @param {string} disciplineId
     */
    async function fetchCurriculum(disciplineId) {
        if (cachedDisciplineId === disciplineId && cachedCurriculum) {
            return cachedCurriculum;
        }
        const res = await fetch(`/api/curriculum/${encodeURIComponent(disciplineId)}`);
        if (!res.ok) return null;
        cachedCurriculum = await res.json();
        cachedDisciplineId = disciplineId;
        return cachedCurriculum;
    }

    function renderList(data) {
        ensureDom();
        const body = document.getElementById("discipline-panel-body");
        const titleEl = document.getElementById("discipline-panel-title");
        if (!body || !titleEl || !data) return;

        titleEl.textContent = data.label || data.discipline;
        body.replaceChildren();

        const lessons = Array.isArray(data.lessons) ? data.lessons : [];
        const visited = getProgress(data.discipline);

        const progress = document.createElement("p");
        progress.className = "discipline-panel__progress";
        const explored = lessons.filter((l) => visited.has(String(l.slug).toLowerCase())).length;
        progress.textContent =
            lessons.length > 0
                ? `${explored} de ${lessons.length} tópicos explorados`
                : "Nenhum tópico no catálogo";
        body.appendChild(progress);

        if (!lessons.length) {
            const empty = document.createElement("p");
            empty.className = "discipline-panel__empty";
            empty.textContent = "Currículo indisponível — catálogo não carregado.";
            body.appendChild(empty);
            return;
        }

        const list = document.createElement("ul");
        list.className = "discipline-panel__list";

        for (const lesson of lessons) {
            const slug = String(lesson.slug || "");
            const done = visited.has(slug.toLowerCase());
            const li = document.createElement("li");
            li.className = "discipline-panel__item";

            const icon = document.createElement("span");
            icon.className = `discipline-panel__check discipline-panel__check--${done ? "done" : "pending"}`;
            icon.setAttribute("aria-hidden", "true");
            if (done) icon.textContent = "✓";

            const label = document.createElement("span");
            label.className = "discipline-panel__lesson";
            label.textContent = lesson.title || slug;

            if (!done) {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "discipline-panel__study";
                btn.append(icon, label);
                btn.addEventListener("click", () => {
                    const cmd = commandForDiscipline(data.discipline) || `/${data.discipline}`;
                    input.value = `${cmd} ${slug.replace(/-/g, " ")} `;
                    input.dispatchEvent(new Event("input"));
                    refreshSiloUi();
                    close();
                    input.focus();
                });
                li.appendChild(btn);
            } else {
                li.append(icon, label);
            }
            list.appendChild(li);
        }

        body.appendChild(list);

        const next = suggestNext(lessons, visited);
        if (next) {
            const cta = document.createElement("button");
            cta.type = "button";
            cta.className = "discipline-panel__next";
            const cmd = commandForDiscipline(data.discipline) || `/${data.discipline}`;
            cta.textContent = `Próximo: ${next.title || next.slug}`;
            cta.addEventListener("click", () => {
                input.value = `${cmd} ${String(next.slug).replace(/-/g, " ")} `;
                input.dispatchEvent(new Event("input"));
                refreshSiloUi();
                close();
                input.focus();
            });
            body.appendChild(cta);
        }
    }

    async function refresh() {
        const id = getDisciplineId();
        if (!id || !panel || panel.hidden) return;
        const data = await fetchCurriculum(id);
        if (data) renderList(data);
    }

    async function showPanel() {
        const id = getDisciplineId();
        if (!id) return;
        open();
        const body = document.getElementById("discipline-panel-body");
        if (body) {
            body.replaceChildren();
            const loading = document.createElement("p");
            loading.className = "discipline-panel__empty";
            loading.textContent = "Carregando trilha…";
            body.appendChild(loading);
        }
        const data = await fetchCurriculum(id);
        if (!data) {
            renderList({
                discipline: id,
                label: labelForDiscipline(id) || id,
                lessons: [],
            });
            return;
        }
        renderList(data);
    }

    function bindOpen(el) {
        if (!el) return;
        el.addEventListener("click", () => {
            if (getDisciplineId()) void showPanel();
        });
        el.addEventListener("keydown", (e) => {
            if (e.key !== "Enter" && e.key !== " ") return;
            if (!getDisciplineId()) return;
            e.preventDefault();
            void showPanel();
        });
    }

    bindOpen(siloPill ?? null);

    return { refresh, close, showPanel };
}
