/**
 * SSOT de disciplinas — espelha core/disciplines.json (manter sincronizado; ver test_discipline_commands).
 */
import catalog from "./disciplines.json" with { type: "json" };

/** @type {Array<{ id: string, label: string, command: string, menuShort?: string, siloClass?: string, menuDescription?: string }>} */
const _items = [...(catalog.disciplines || [])].sort(
    (a, b) => (b.command?.length || 0) - (a.command?.length || 0),
);

export const DISCIPLINES = _items;

/**
 * @param {string | undefined} disciplineId
 * @returns {string}
 */
export function commandForDiscipline(disciplineId) {
    const key = (disciplineId || "").trim().toLowerCase();
    const row = _items.find((d) => d.id === key);
    return row?.command || "";
}

/**
 * @param {string | undefined} disciplineId
 * @returns {string} ex.: `/python `
 */
export function scopePrefixForDiscipline(disciplineId) {
    const cmd = commandForDiscipline(disciplineId);
    return cmd ? `${cmd} ` : "";
}

/**
 * Prefixos ordenados (mais longo primeiro) para labels imediatos.
 */
export const DISCIPLINE_PREFIXES = _items.map((d) => [d.command, d.label]);

/**
 * Mapa silo CSS suffix por comando.
 */
export const DISCIPLINE_SILO_BY_COMMAND = Object.fromEntries(
    _items.map((d) => [d.command, d.siloClass || d.id]),
);
