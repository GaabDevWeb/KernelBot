import {
    activeDisciplineFromInput,
    activeDisciplineIdFromInput,
    siloClassSuffix,
    siloDisplayName,
} from "../utils/contextLabel.js";
import { syncDisciplineQueryParam } from "../utils/deepLink.js";
import { isLanding } from "../utils/uiState.js";

/**
 * @param {{
 *   input: HTMLTextAreaElement,
 *   inputArea: HTMLElement | null,
 *   siloPill: HTMLElement | null,
 *   activeDisciplineBadge: HTMLElement | null,
 *   scopeBtn: HTMLElement | null,
 *   contextStack: HTMLElement | null,
 *   refreshContextStack: () => void,
 *   hidePinBadge?: () => void,
 * }} deps
 */
export function createComposerController(deps) {
    const {
        input,
        inputArea,
        siloPill,
        activeDisciplineBadge,
        scopeBtn,
        refreshContextStack,
        hidePinBadge,
    } = deps;

    const SILO_CLASS_PREFIX = "input-area--silo-";
    /** @type {string | null} */
    let prevDisciplineId = null;

    function refreshSiloUi() {
        if (!inputArea) return;
        [...inputArea.classList].forEach((c) => {
            if (c === "input-area--silo" || c.startsWith(SILO_CLASS_PREFIX)) {
                inputArea.classList.remove(c);
            }
        });
        const active = activeDisciplineFromInput(input.value);
        const suffix = siloClassSuffix(input.value);
        const currentDisciplineId = activeDisciplineIdFromInput(input.value);

        if (
            prevDisciplineId &&
            currentDisciplineId &&
            prevDisciplineId !== currentDisciplineId &&
            hidePinBadge
        ) {
            hidePinBadge();
        }
        prevDisciplineId = currentDisciplineId;

        if (suffix && siloPill) {
            inputArea.classList.add("input-area--silo", SILO_CLASS_PREFIX + suffix);
            siloPill.hidden = false;
            siloPill.classList.add("silo-pill--interactive");
            siloPill.setAttribute("role", "button");
            siloPill.setAttribute("tabindex", "0");
            siloPill.setAttribute("title", "Ver mapa da disciplina");
            const name = siloDisplayName(input.value);
            if (active?.command) {
                siloPill.innerHTML =
                    `<span class="silo-pill__label">Disciplina ativa:</span> ` +
                    `<span class="silo-pill__name">${name || active.label}</span> ` +
                    `<code class="silo-pill__cmd">${active.command}</code>`;
            } else {
                siloPill.textContent = name ? `Disciplina ativa: ${name}` : "";
            }
        } else if (siloPill) {
            siloPill.hidden = true;
            siloPill.textContent = "";
            siloPill.classList.remove("silo-pill--interactive");
            siloPill.removeAttribute("role");
            siloPill.removeAttribute("tabindex");
            siloPill.removeAttribute("title");
        }

        /* Canonical Layout: header badge only during landing (empty-state). */
        if (activeDisciplineBadge) {
            const labelEl = activeDisciplineBadge.querySelector(".active-discipline-badge__label");
            const cmdEl = activeDisciplineBadge.querySelector(".active-discipline-badge__cmd");
            const showInHeader = Boolean(active) && isLanding();
            if (showInHeader) {
                activeDisciplineBadge.hidden = false;
                if (labelEl) labelEl.textContent = active.label;
                if (cmdEl) cmdEl.textContent = active.command;
                activeDisciplineBadge.title = `Buscando em: ${active.label}`;
            } else {
                activeDisciplineBadge.hidden = true;
                if (labelEl) labelEl.textContent = "";
                if (cmdEl) cmdEl.textContent = "";
                activeDisciplineBadge.removeAttribute("title");
            }
        }

        if (scopeBtn) {
            scopeBtn.classList.toggle("scope-btn--active", Boolean(active));
            scopeBtn.setAttribute(
                "aria-label",
                active
                    ? `Matéria: ${active.label}. Abrir seletor de escopo`
                    : "Selecionar matéria da busca",
            );
        }

        syncDisciplineQueryParam(currentDisciplineId);
        refreshContextStack();
    }

    function getActiveDisciplineId() {
        return activeDisciplineIdFromInput(input.value);
    }

    return { refreshSiloUi, getActiveDisciplineId, SILO_CLASS_PREFIX };
}
