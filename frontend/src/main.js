import { loadDisciplinesCatalog } from "./config/disciplines.js";
import { initTheme } from "./utils/theme.js";
import { init } from "./ui.js";
import { initScopeMenu } from "./scopeMenu.js";
import { initOnboarding } from "./onboarding.js";
import { setIssLessonBase } from "./utils/issLinks.js";
import { showToast } from "./utils/toast.js";
import { initCatalogFromConfig, isCatalogAvailable } from "./utils/catalogAvailability.js";

/**
 * @returns {Promise<boolean>}
 */
async function loadPublicConfig() {
    let catalogEnabled = false;
    try {
        const res = await fetch("/api/public-config");
        if (!res.ok) {
            initCatalogFromConfig(false);
            return false;
        }
        const data = await res.json();
        if (data?.iss_lesson_base) setIssLessonBase(data.iss_lesson_base);
        catalogEnabled = Boolean(data?.catalog_enabled);
        initCatalogFromConfig(catalogEnabled);
    } catch {
        initCatalogFromConfig(false);
    }
    return catalogEnabled;
}

async function boot() {
    initTheme();
    await loadDisciplinesCatalog();
    const catalogEnabled = await loadPublicConfig();
    if (catalogEnabled) {
        await isCatalogAvailable();
    }
    initScopeMenu();
    initOnboarding();
    init();
    if (typeof window !== "undefined") {
        window.showToast = showToast;
    }
}

boot().catch((err) => {
    console.error("[Kernel] Falha no boot:", err);
});
