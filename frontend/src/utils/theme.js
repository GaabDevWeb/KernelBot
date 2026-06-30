const STORAGE_KEY = "kernel-theme";

/** @returns {"dark" | "light"} */
export function getTheme() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
}

/** @param {"dark" | "light"} theme */
export function setTheme(theme) {
    const next = theme === "light" ? "light" : "dark";

    if (next === "light") {
        document.documentElement.setAttribute("data-theme", "light");
    } else {
        document.documentElement.removeAttribute("data-theme");
    }

    document.documentElement.style.colorScheme = next;

    try {
        localStorage.setItem(STORAGE_KEY, next);
    } catch {
        /* storage indisponível */
    }

    window.dispatchEvent(new CustomEvent("kernel:theme-change", { detail: { theme: next } }));
    refreshThemeToggle();
}

export function toggleTheme() {
    setTheme(getTheme() === "dark" ? "light" : "dark");
}

/** Aplica preferência salva e liga o botão de alternância. */
export function initTheme() {
    let saved = "dark";
    try {
        saved = localStorage.getItem(STORAGE_KEY) || "dark";
    } catch {
        /* storage indisponível */
    }

    setTheme(saved === "light" ? "light" : "dark");
    bindThemeToggle();
}

function bindThemeToggle() {
    const btn = document.getElementById("theme-toggle");
    if (!btn || btn.dataset.bound === "1") return;
    btn.dataset.bound = "1";
    btn.addEventListener("click", () => toggleTheme());
    refreshThemeToggle();
}

function refreshThemeToggle() {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;

    const isLight = getTheme() === "light";
    btn.setAttribute("aria-label", isLight ? "Ativar tema escuro" : "Ativar tema claro");
    btn.setAttribute("title", isLight ? "Tema escuro" : "Tema claro");
    btn.classList.toggle("theme-toggle--light", isLight);
}
