const OVERLAY_ID = "shortcuts-overlay";
const TOGGLE_ID = "shortcuts-toggle";

/** @type {HTMLElement | null} */
let overlayEl = null;

/** @type {HTMLButtonElement | null} */
let toggleBtn = null;

function isEditableTarget(target) {
    if (!(target instanceof HTMLElement)) return false;
    const tag = target.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || target.isContentEditable;
}

function refreshToggleExpanded(expanded) {
    if (!toggleBtn) return;
    toggleBtn.setAttribute("aria-expanded", expanded ? "true" : "false");
}

function ensureOverlay() {
    if (overlayEl && document.body.contains(overlayEl)) return overlayEl;

    overlayEl = document.createElement("div");
    overlayEl.id = OVERLAY_ID;
    overlayEl.className = "shortcuts-overlay";
    overlayEl.hidden = true;
    overlayEl.setAttribute("role", "dialog");
    overlayEl.setAttribute("aria-modal", "true");
    overlayEl.setAttribute("aria-label", "Atalhos de teclado");

    overlayEl.innerHTML = `
        <div class="shortcuts-overlay__panel">
            <div class="shortcuts-overlay__head">
                <h2 class="shortcuts-overlay__title">Atalhos</h2>
                <button type="button" class="shortcuts-overlay__close" aria-label="Fechar">×</button>
            </div>
            <ul class="shortcuts-overlay__list">
                <li><kbd>Enter</kbd> Enviar mensagem</li>
                <li><kbd>Shift</kbd> + <kbd>Enter</kbd> Nova linha</li>
                <li>Botão <kbd>?</kbd> ou <kbd>Ctrl</kbd> + <kbd>/</kbd> Mostrar atalhos</li>
                <li><kbd>Esc</kbd> Fechar painéis</li>
            </ul>
        </div>
    `;

    overlayEl.addEventListener("click", (e) => {
        if (e.target === overlayEl) hideShortcutsOverlay();
    });
    overlayEl.querySelector(".shortcuts-overlay__close")?.addEventListener("click", hideShortcutsOverlay);

    document.body.appendChild(overlayEl);
    return overlayEl;
}

export function showShortcutsOverlay() {
    const el = ensureOverlay();
    el.hidden = false;
    refreshToggleExpanded(true);
    el.querySelector(".shortcuts-overlay__close")?.focus();
}

export function hideShortcutsOverlay() {
    if (!overlayEl) return;
    overlayEl.hidden = true;
    refreshToggleExpanded(false);
    toggleBtn?.focus();
}

export function toggleShortcutsOverlay() {
    const el = ensureOverlay();
    if (el.hidden) showShortcutsOverlay();
    else hideShortcutsOverlay();
}

function bindShortcutsToggle() {
    toggleBtn = /** @type {HTMLButtonElement | null} */ (document.getElementById(TOGGLE_ID));
    if (!toggleBtn || toggleBtn.dataset.bound === "1") return;
    toggleBtn.dataset.bound = "1";
    toggleBtn.addEventListener("click", () => toggleShortcutsOverlay());
}

export function initShortcutsOverlay() {
    ensureOverlay();
    bindShortcutsToggle();

    document.addEventListener("keydown", (e) => {
        if (overlayEl && !overlayEl.hidden && e.key === "Escape") {
            e.preventDefault();
            hideShortcutsOverlay();
            return;
        }

        if (isEditableTarget(e.target)) {
            if ((e.ctrlKey || e.metaKey) && e.key === "/") {
                e.preventDefault();
                toggleShortcutsOverlay();
            }
            return;
        }

        if (e.key === "?" && !e.ctrlKey && !e.metaKey && !e.altKey) {
            e.preventDefault();
            toggleShortcutsOverlay();
            return;
        }

        if ((e.ctrlKey || e.metaKey) && e.key === "/") {
            e.preventDefault();
            toggleShortcutsOverlay();
        }
    });
}
