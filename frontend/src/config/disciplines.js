/**
 * Catálogo de disciplinas — carregado de core/disciplines.json via HTTP (SSOT no backend).
 */

/** @type {Array<{ id: string, label: string, command: string, menuShort?: string, siloClass?: string, menuDescription?: string }>} */
let _items = [];

/** @type {Promise<void> | null} */
let _loadPromise = null;

function sortItems(items) {
    return [...items].sort((a, b) => (b.command?.length || 0) - (a.command?.length || 0));
}

/**
 * Carrega o catálogo do servidor. Idempotente.
 * @returns {Promise<void>}
 */
export function loadDisciplinesCatalog() {
    if (_items.length) return Promise.resolve();
    if (_loadPromise) return _loadPromise;

    _loadPromise = fetch("/src/config/disciplines.json")
        .then((res) => {
            if (!res.ok) throw new Error(`disciplines.json HTTP ${res.status}`);
            return res.json();
        })
        .then((catalog) => {
            _items = sortItems(catalog?.disciplines || []);
        })
        .catch((err) => {
            _loadPromise = null;
            throw err;
        });

    return _loadPromise;
}

export function getDisciplines() {
    return _items;
}

/** @deprecated Use getDisciplines() após loadDisciplinesCatalog() */
export const DISCIPLINES = new Proxy([], {
    get(_target, prop) {
        const arr = _items;
        const value = Reflect.get(arr, prop, arr);
        return typeof value === "function" ? value.bind(arr) : value;
    },
});

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
export function getDisciplinePrefixes() {
    return _items.map((d) => [d.command, d.label]);
}

/** @deprecated Use getDisciplinePrefixes() */
export const DISCIPLINE_PREFIXES = new Proxy([], {
    get(_target, prop) {
        const arr = getDisciplinePrefixes();
        const value = Reflect.get(arr, prop, arr);
        return typeof value === "function" ? value.bind(arr) : value;
    },
});

/**
 * Mapa silo CSS suffix por comando.
 */
export function getDisciplineSiloByCommand() {
    return Object.fromEntries(_items.map((d) => [d.command, d.siloClass || d.id]));
}

/** @deprecated Use getDisciplineSiloByCommand() */
export const DISCIPLINE_SILO_BY_COMMAND = new Proxy(
    {},
    {
        get(_target, prop) {
            return getDisciplineSiloByCommand()[prop];
        },
        ownKeys() {
            return Reflect.ownKeys(getDisciplineSiloByCommand());
        },
        getOwnPropertyDescriptor(_target, prop) {
            const map = getDisciplineSiloByCommand();
            if (prop in map) {
                return { configurable: true, enumerable: true, value: map[prop] };
            }
            return undefined;
        },
    },
);
