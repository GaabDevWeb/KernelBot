/** Toast utilitário — feedback não bloqueante com aria-live. */

/** @type {HTMLElement | null} */
let container = null;
/** @type {ReturnType<typeof setTimeout> | null} */
let dismissTimer = null;

function ensureContainer() {
    if (container && document.body.contains(container)) return container;
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    container.setAttribute("aria-live", "polite");
    container.setAttribute("aria-atomic", "true");
    document.body.appendChild(container);
    return container;
}

/**
 * @param {string} message
 * @param {{ duration?: number, actionLabel?: string, onAction?: () => void }} [opts]
 */
export function showToast(message, opts = {}) {
    const root = ensureContainer();
    const duration = opts.duration ?? 3000;

    root.replaceChildren();

    if (dismissTimer) {
        clearTimeout(dismissTimer);
        dismissTimer = null;
    }

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.setAttribute("role", "status");

    const text = document.createElement("span");
    text.className = "toast__message";
    text.textContent = message;
    toast.appendChild(text);

    if (opts.actionLabel && typeof opts.onAction === "function") {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "toast__action";
        btn.textContent = opts.actionLabel;
        btn.addEventListener("click", () => {
            opts.onAction?.();
            toast.remove();
            if (dismissTimer) clearTimeout(dismissTimer);
        });
        toast.appendChild(btn);
    }

    root.appendChild(toast);

    dismissTimer = setTimeout(() => {
        toast.classList.add("toast--dismiss");
        toast.addEventListener(
            "transitionend",
            () => toast.remove(),
            { once: true },
        );
        dismissTimer = null;
    }, duration);
}
