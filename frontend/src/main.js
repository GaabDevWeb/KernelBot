import { loadDisciplinesCatalog } from "./config/disciplines.js";
import { init } from "./ui.js";
import { initScopeMenu } from "./scopeMenu.js";
import { initOnboarding } from "./onboarding.js";
import { setIssLessonBase } from "./utils/issLinks.js";
import { showToast } from "./utils/toast.js";

async function loadPublicConfig() {
    try {
        const res = await fetch("/api/public-config");
        if (!res.ok) return;
        const data = await res.json();
        if (data?.iss_lesson_base) setIssLessonBase(data.iss_lesson_base);
    } catch {
        /* offline / staging parcial */
    }
}

async function boot() {
    await Promise.all([loadDisciplinesCatalog(), loadPublicConfig()]);
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
