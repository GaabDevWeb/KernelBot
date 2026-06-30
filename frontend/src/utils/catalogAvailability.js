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

/**
 * Desativa #scope-btn quando o catálogo está off ou indisponível.
 */
export function applyCatalogScopeUi() {
    const disabled = getCatalogAvailableSync() === false;
    const scopeBtn = document.getElementById("scope-btn");
    if (!scopeBtn) return;

    scopeBtn.disabled = disabled;
    scopeBtn.setAttribute("aria-disabled", disabled ? "true" : "false");
    scopeBtn.classList.toggle("scope-btn--disabled", disabled);

    if (disabled) {
        scopeBtn.setAttribute("title", CATALOG_UNAVAILABLE_TITLE);
        scopeBtn.setAttribute("aria-label", CATALOG_UNAVAILABLE_TITLE);
        scopeBtn.setAttribute("aria-expanded", "false");
    } else {
        scopeBtn.removeAttribute("title");
    }
}

export { CATALOG_UNAVAILABLE_TITLE };
