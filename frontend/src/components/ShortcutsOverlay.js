const OVERLAY_ID = "shortcuts-overlay";

/** @type {HTMLElement | null} */
let overlayEl = null;

function isEditableTarget(target) {
    if (!(target instanceof HTMLElement)) return false;
    const tag = target.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || target.isContentEditable;
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
                <li><kbd>?</kbd> ou <kbd>Ctrl</kbd> + <kbd>/</kbd> Mostrar atalhos</li>
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
    el.querySelector(".shortcuts-overlay__close")?.focus();
}

export function hideShortcutsOverlay() {
    if (!overlayEl) return;
    overlayEl.hidden = true;
}

export function toggleShortcutsOverlay() {
    const el = ensureOverlay();
    if (el.hidden) showShortcutsOverlay();
    else hideShortcutsOverlay();
}

export function initShortcutsOverlay() {
    ensureOverlay();

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
                return;
            }
            if (e.key === "?" && !e.ctrlKey && !e.metaKey && !e.altKey) {
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
