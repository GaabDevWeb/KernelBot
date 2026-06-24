/**
 * Deep links ?d=python ou ?discipline=python
 */
import { commandForDiscipline, getDisciplines } from "../config/disciplines.js";

/**
 * @returns {string | null} discipline id
 */
export function disciplineIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const raw = (params.get("d") || params.get("discipline") || "").trim().toLowerCase();
    if (!raw) return null;
    const items = getDisciplines();
    const exact = items.find((d) => d.id === raw);
    if (exact) return exact.id;
    const byCmd = items.find((d) => d.command === `/${raw}` || d.command.slice(1) === raw);
    return byCmd?.id ?? null;
}

/**
 * @param {HTMLTextAreaElement} input
 * @param {(disciplineId: string) => void} [onApplied]
 * @returns {boolean}
 */
export function applyDisciplineDeepLink(input, onApplied) {
    const id = disciplineIdFromUrl();
    if (!id || !input) return false;
    const cmd = commandForDiscipline(id);
    if (!cmd) return false;
    input.value = `${cmd} `;
    input.dispatchEvent(new Event("input"));
    onApplied?.(id);
    return true;
}

/**
 * @param {string | null | undefined} disciplineId
 */
export function syncDisciplineQueryParam(disciplineId) {
    const url = new URL(window.location.href);
    if (disciplineId) {
        url.searchParams.set("d", disciplineId);
    } else {
        url.searchParams.delete("d");
        url.searchParams.delete("discipline");
    }
    window.history.replaceState({}, "", url);
}
