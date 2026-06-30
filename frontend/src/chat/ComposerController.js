import {
    activeDisciplineFromInput,
    activeDisciplineIdFromInput,
    siloClassSuffix,
    siloDisplayName,
} from "../utils/contextLabel.js";
import { commandForDiscipline, getDisciplines, labelForDiscipline } from "../config/disciplines.js";
import { getCatalogAvailableSync } from "../utils/catalogAvailability.js";

/**
 * @param {{
 *   input: HTMLTextAreaElement,
 *   inputArea: HTMLElement | null,
 *   siloPill: HTMLElement | null,
 *   scopeBtn: HTMLElement | null,
 *   contextStack: HTMLElement | null,
 *   refreshContextStack: () => void,
 *   hidePinBadge?: () => void,
 *   onDisciplineChange?: (disciplineId: string | null) => void,
 *   getStoredDisciplineId?: () => string | null,
 *   setStoredDisciplineId?: (disciplineId: string | null) => void,
 * }} deps
 */
export function createComposerController(deps) {
    const {
        input,
        inputArea,
        siloPill,
        scopeBtn,
        refreshContextStack,
        hidePinBadge,
        onDisciplineChange,
        getStoredDisciplineId = () => null,
        setStoredDisciplineId,
    } = deps;

    const SILO_CLASS_PREFIX = "input-area--silo-";
    /** @type {string | null} */
    let prevDisciplineId = null;

    function resolveActiveDiscipline() {
        const fromInput = activeDisciplineFromInput(input.value);
        if (fromInput) return fromInput;
        const storedId = getStoredDisciplineId();
        if (!storedId) return null;
        const row = getDisciplines().find((d) => d.id === storedId);
        if (!row) {
            return {
                command: commandForDiscipline(storedId),
                label: labelForDiscipline(storedId) || storedId,
            };
        }
        return { command: row.command, label: row.label };
    }

    function resolveDisciplineId() {
        const fromInput = activeDisciplineIdFromInput(input.value);
        if (fromInput) return fromInput;
        return getStoredDisciplineId();
    }

    function resolveSiloSuffix() {
        const suffix = siloClassSuffix(input.value);
        if (suffix) return suffix;
        const storedId = getStoredDisciplineId();
        if (!storedId) return null;
        const row = getDisciplines().find((d) => d.id === storedId);
        return row?.siloClass || storedId;
    }

    function resolveSiloDisplayName() {
        const name = siloDisplayName(input.value);
        if (name) return name;
        const active = resolveActiveDiscipline();
        return active?.label || null;
    }

    function persistDisciplineIfChanged() {
        if (!setStoredDisciplineId) return;
        const currentId = resolveDisciplineId();
        const stored = getStoredDisciplineId();
        if (currentId !== stored) {
            setStoredDisciplineId(currentId);
        }
    }

    function refreshSiloUi() {
        if (!inputArea) return;
        [...inputArea.classList].forEach((c) => {
            if (c === "input-area--silo" || c.startsWith(SILO_CLASS_PREFIX)) {
                inputArea.classList.remove(c);
            }
        });
        const active = resolveActiveDiscipline();
        const suffix = resolveSiloSuffix();
        const currentDisciplineId = resolveDisciplineId();

        persistDisciplineIfChanged();

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
            const catalogOn = getCatalogAvailableSync() !== false;
            if (catalogOn) {
                siloPill.classList.add("silo-pill--interactive");
                siloPill.setAttribute("role", "button");
                siloPill.setAttribute("tabindex", "0");
                siloPill.setAttribute("title", "Ver mapa da disciplina");
            } else {
                siloPill.classList.remove("silo-pill--interactive");
                siloPill.removeAttribute("role");
                siloPill.removeAttribute("tabindex");
                siloPill.removeAttribute("title");
            }
            const name = resolveSiloDisplayName();
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

        if (scopeBtn) {
            scopeBtn.classList.toggle("scope-btn--active", Boolean(active));
            scopeBtn.setAttribute(
                "aria-label",
                active
                    ? `Matéria: ${active.label}. Abrir seletor de escopo`
                    : "Selecionar matéria da busca",
            );
        }

        onDisciplineChange?.(currentDisciplineId);
        refreshContextStack();
    }

    function getActiveDisciplineId() {
        return resolveDisciplineId();
    }

    return { refreshSiloUi, getActiveDisciplineId, SILO_CLASS_PREFIX, persistDisciplineIfChanged };
}
