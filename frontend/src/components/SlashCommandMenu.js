import { DISCIPLINES } from "../config/disciplines.js";
import { stripLeadingDisciplineCommand } from "../scopeMenu.js";

const EXTRA_COMMANDS = [
    { command: "/doc", label: "Documentação", description: "Documentação interna do sistema" },
    { command: "/content", label: "Base geral", description: "Busca em todo o conteúdo indexado" },
];

/**
 * @returns {Array<{ command: string, label: string, description: string }>}
 */
function allCommands() {
    const fromDisc = DISCIPLINES.map((d) => ({
        command: d.command,
        label: d.label,
        description: d.menuDescription || d.label,
    }));
    return [...fromDisc, ...EXTRA_COMMANDS];
}

/**
 * @param {string} inputValue
 * @returns {string | null}
 */
function activeSlashQuery(inputValue) {
    const trimmed = (inputValue || "").trimStart();
    if (!trimmed.startsWith("/")) return null;
    const space = trimmed.indexOf(" ");
    if (space !== -1) return null;
    return trimmed.slice(1).toLowerCase();
}

/**
 * @param {HTMLElement} input
 * @param {HTMLElement} anchor
 */
export function createSlashCommandMenu(input, anchor) {
    const menu = document.createElement("div");
    menu.id = "slash-command-menu";
    menu.className = "slash-command-menu";
    menu.setAttribute("role", "listbox");
    menu.hidden = true;
    anchor.appendChild(menu);

    let filtered = [];
    let activeIndex = 0;

    function hide() {
        menu.hidden = true;
        menu.replaceChildren();
        filtered = [];
        activeIndex = 0;
        document.getElementById("empty-state")?.classList.remove("empty-state--slash-open");
    }

    function render() {
        menu.replaceChildren();
        if (!filtered.length) {
            hide();
            return;
        }
        menu.hidden = false;
        document.getElementById("empty-state")?.classList.add("empty-state--slash-open");
        filtered.forEach((item, i) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "slash-command-option";
            btn.setAttribute("role", "option");
            btn.dataset.cmd = item.command;
            if (i === activeIndex) {
                btn.classList.add("slash-command-option--active");
                btn.setAttribute("aria-selected", "true");
            } else {
                btn.setAttribute("aria-selected", "false");
            }
            btn.setAttribute(
                "aria-label",
                `${item.command} — ${item.label}. ${item.description}`,
            );
            btn.innerHTML =
                `<span class="slash-command-option__row">` +
                `<span class="slash-command-option__cmd">${item.command}</span>` +
                `<span class="slash-command-option__label">${item.label}</span>` +
                `</span>` +
                `<span class="slash-command-option__desc">${item.description}</span>`;
            btn.addEventListener("mousedown", (e) => {
                e.preventDefault();
                select(item.command);
            });
            menu.appendChild(btn);
        });
    }

    function select(command) {
        const tail = stripLeadingDisciplineCommand(input.value);
        input.value = tail ? `${command} ${tail}` : `${command} `;
        input.dispatchEvent(new Event("input"));
        hide();
        input.focus();
        const len = input.value.length;
        input.selectionStart = input.selectionEnd = len;
    }

    function refresh() {
        const q = activeSlashQuery(input.value);
        if (q === null) {
            hide();
            return false;
        }
        const needle = q;
        filtered = allCommands().filter(
            (item) =>
                item.command.slice(1).toLowerCase().includes(needle) ||
                item.label.toLowerCase().includes(needle),
        );
        activeIndex = Math.min(activeIndex, Math.max(0, filtered.length - 1));
        render();
        return filtered.length > 0;
    }

    function move(delta) {
        if (!filtered.length) return;
        activeIndex = (activeIndex + delta + filtered.length) % filtered.length;
        render();
    }

    input.addEventListener("input", () => {
        activeIndex = 0;
        refresh();
    });

    input.addEventListener("keydown", (e) => {
        if (menu.hidden || !filtered.length) return;
        if (e.key === "ArrowDown") {
            e.preventDefault();
            move(1);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            move(-1);
        } else if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            e.stopImmediatePropagation();
            select(filtered[activeIndex].command);
        } else if (e.key === "Escape") {
            hide();
        } else if (e.key === "Tab" && filtered[activeIndex]) {
            e.preventDefault();
            select(filtered[activeIndex].command);
        }
    });

    document.addEventListener("click", (e) => {
        if (!menu.hidden && !menu.contains(/** @type {Node} */ (e.target)) && e.target !== input) {
            hide();
        }
    });

    return { refresh, hide, select };
}
