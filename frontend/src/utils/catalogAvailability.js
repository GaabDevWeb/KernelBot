/** @type {boolean | null} */
let catalogAvailable = null;

/**
 * Inicializa disponibilidade a partir de public-config (sem probe de rede).
 * @param {boolean} enabled
 */
export function initCatalogFromConfig(enabled) {
    catalogAvailable = enabled ? null : false;
}

/**
 * @returns {Promise<boolean>}
 */
export async function isCatalogAvailable() {
    if (catalogAvailable !== null) return catalogAvailable;
    try {
        const res = await fetch("/api/curriculum");
        catalogAvailable = res.ok;
    } catch {
        catalogAvailable = false;
    }
    return catalogAvailable;
}

/**
 * @returns {boolean | null}
 */
export function getCatalogAvailableSync() {
    return catalogAvailable;
}

const CATALOG_UNAVAILABLE_TITLE = "Mapa curricular indisponível";

export { CATALOG_UNAVAILABLE_TITLE };
