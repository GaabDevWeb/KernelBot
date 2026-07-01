/**
 * Deep links ?d=python, ?c=<conversationId>
 */
import { commandForDiscipline, getDisciplines } from "../config/disciplines.js";
import { switchConversation } from "./conversations.js";
import { showToast } from "./toast.js";

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
 * @returns {string | null}
 */
export function conversationIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const raw = (params.get("c") || "").trim();
    return raw || null;
}

/**
 * @returns {boolean} false se o parâmetro ?d= existe mas é inválido (URL limpa).
 */
export function rejectInvalidDisciplineDeepLink() {
    const params = new URLSearchParams(window.location.search);
    const raw = (params.get("d") || params.get("discipline") || "").trim();
    if (!raw) return true;
    if (disciplineIdFromUrl()) return true;

    showToast("Disciplina inválida no link compartilhado");
    const url = new URL(window.location.href);
    url.searchParams.delete("d");
    url.searchParams.delete("discipline");
    window.history.replaceState({}, "", url);
    return false;
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
 * @param {() => void} onApplied
 * @returns {boolean}
 */
export function applyConversationDeepLink(onApplied) {
    const id = conversationIdFromUrl();
    if (!id) return false;
    const conv = switchConversation(id);
    if (conv) onApplied?.();
    return Boolean(conv);
}

/**
 * @param {{ conversationId?: string | null, disciplineId?: string | null }} state
 */
export function syncUrlState(state) {
    const url = new URL(window.location.href);
    if ("conversationId" in state) {
        if (state.conversationId) {
            url.searchParams.set("c", state.conversationId);
        } else {
            url.searchParams.delete("c");
        }
    }
    if ("disciplineId" in state) {
        if (state.disciplineId) {
            url.searchParams.set("d", state.disciplineId);
        } else {
            url.searchParams.delete("d");
            url.searchParams.delete("discipline");
        }
    }
    window.history.replaceState({}, "", url);
}

/**
 * @param {string | null | undefined} disciplineId
 */
export function syncDisciplineQueryParam(disciplineId) {
    syncUrlState({
        conversationId: conversationIdFromUrl(),
        disciplineId: disciplineId || null,
    });
}
