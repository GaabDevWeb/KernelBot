/**
 * Menu de escopo gerado a partir de disciplines.json (SSOT).
 */
import { DISCIPLINES } from "./config/disciplines.js";

/** @type {string[]} */
const COMMAND_PREFIXES = DISCIPLINES.map((d) => d.command).sort(
    (a, b) => b.length - a.length,
);

/**
 * Remove o prefixo de disciplina mais longo que casar no início da mensagem.
 * @param {string} text
 * @returns {string}
 */
export function stripLeadingDisciplineCommand(text) {
    const trimmed = (text || "").trimStart();
    for (const cmd of COMMAND_PREFIXES) {
        if (!trimmed.startsWith(cmd)) continue;
        const tail = trimmed.slice(cmd.length);
        if (tail.length > 0 && !tail[0].match(/\s/)) continue;
        return tail.trimStart();
    }
    if (trimmed.startsWith("/doc")) {
        const tail = trimmed.slice(4);
        if (!tail.length || tail[0].match(/\s/)) return tail.trimStart();
    }
    if (trimmed.startsWith("/content")) {
        const tail = trimmed.slice(8);
        if (!tail.length || tail[0].match(/\s/)) return tail.trimStart();
    }
    return trimmed;
}

/**
 * @param {HTMLElement | null} menuRoot
 */
function renderScopeOptions(menuRoot) {
    if (!menuRoot) return;
    menuRoot.replaceChildren();

    for (const d of [...DISCIPLINES].sort((a, b) =>
        a.label.localeCompare(b.label, "pt-BR"),
    )) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.role = "menuitem";
        btn.dataset.cmd = d.command;
        btn.className =
            "scope-option rounded-xl w-full text-left px-4 py-2.5 flex flex-col gap-0.5 cursor-pointer";

        const cmdEl = document.createElement("span");
        cmdEl.className = "text-sm font-semibold scope-option-cmd";
        cmdEl.textContent = d.command;

        const descEl = document.createElement("span");
        descEl.className = "text-xs leading-snug scope-option-desc";
        const desc = d.menuDescription || d.label;
        if (d.menuShort && d.menuShort !== d.command) {
            descEl.textContent = `${desc} · atalho comum: ${d.menuShort}`;
        } else {
            descEl.textContent = desc;
        }

        btn.append(cmdEl, descEl);
        menuRoot.appendChild(btn);
    }

    const docBtn = document.createElement("button");
    docBtn.type = "button";
    docBtn.role = "menuitem";
    docBtn.dataset.cmd = "/doc";
    docBtn.className =
        "scope-option rounded-xl w-full text-left px-4 py-2.5 flex flex-col gap-0.5 cursor-pointer";
    docBtn.innerHTML =
        '<span class="text-sm font-semibold scope-option-cmd">/doc</span>' +
        '<span class="text-xs leading-snug scope-option-desc">Documentação interna do sistema</span>';
    menuRoot.appendChild(docBtn);
}

/**
 * @param {{ onScopeChange?: () => void }} [opts]
 */
export function initScopeMenu(opts = {}) {
    const btn = document.getElementById("scope-btn");
    const menu = document.getElementById("scope-menu");
    const menuList = document.getElementById("scope-menu-list");
    const input = document.getElementById("message-input");
    const selector = document.getElementById("scope-selector");

    renderScopeOptions(menuList);

    if (!btn || !menu || !input) return;

    function openMenu() {
        menu.classList.add("open");
        btn.setAttribute("aria-expanded", "true");
    }

    function closeMenu() {
        menu.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
    }

    btn.addEventListener("click", (e) => {
        e.stopPropagation();
        menu.classList.contains("open") ? closeMenu() : openMenu();
    });

    menu.querySelectorAll(".scope-option").forEach((opt) => {
        opt.addEventListener("click", () => {
            const cmd = String(opt.dataset.cmd || "").trim();
            if (!cmd) return;
            const stripped = stripLeadingDisciplineCommand(input.value);
            input.value = stripped ? `${cmd} ${stripped}` : `${cmd} `;
            input.dispatchEvent(new Event("input"));
            opts.onScopeChange?.();
            closeMenu();
            input.focus();
            input.selectionStart = input.selectionEnd = input.value.length;
        });
    });

    document.addEventListener("click", (e) => {
        if (selector && !selector.contains(/** @type {Node} */ (e.target))) {
            closeMenu();
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeMenu();
    });
}
