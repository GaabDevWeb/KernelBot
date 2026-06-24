import { loadDisciplinesCatalog } from "./config/disciplines.js";
import { init } from "./ui.js";
import { initScopeMenu } from "./scopeMenu.js";
import { initOnboarding } from "./onboarding.js";

async function boot() {
    await loadDisciplinesCatalog();
    initScopeMenu();
    initOnboarding();
    init();
}

boot().catch((err) => {
    console.error("[Kernel] Falha no boot:", err);
});
