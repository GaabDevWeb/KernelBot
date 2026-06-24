import { createConversation, listConversations, switchConversation } from "../utils/conversations.js";

/**
 * @param {{
 *   sidebar: HTMLElement | null,
 *   listEl: HTMLElement | null,
 *   overlay: HTMLElement | null,
 *   toggleBtn: HTMLElement | null,
 *   newBtn: HTMLElement | null,
 *   getActiveId: () => string | null,
 *   onSelect: (id: string) => void,
 *   onNew: () => void,
 * }} opts
 */
export function createConversationSidebar(opts) {
    const { sidebar, listEl, overlay, toggleBtn, newBtn, getActiveId, onSelect, onNew } =
        opts;

    function closeMobile() {
        sidebar?.classList.remove("conversation-sidebar--open");
        overlay?.classList.remove("sidebar-overlay--visible");
    }

    function openMobile() {
        sidebar?.classList.add("conversation-sidebar--open");
        overlay?.classList.add("sidebar-overlay--visible");
    }

    function render() {
        if (!listEl) return;
        listEl.replaceChildren();
        const activeId = getActiveId();
        for (const conv of listConversations()) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "conversation-sidebar__item";
            btn.setAttribute("role", "listitem");
            if (conv.id === activeId) btn.classList.add("conversation-sidebar__item--active");
            btn.textContent = conv.title || "Nova conversa";
            btn.title = conv.title || "Nova conversa";
            btn.addEventListener("click", () => {
                if (conv.id === activeId) {
                    closeMobile();
                    return;
                }
                switchConversation(conv.id);
                onSelect(conv.id);
                render();
                closeMobile();
            });
            listEl.appendChild(btn);
        }
    }

    toggleBtn?.addEventListener("click", () => {
        if (sidebar?.classList.contains("conversation-sidebar--open")) closeMobile();
        else openMobile();
    });

    overlay?.addEventListener("click", closeMobile);

    newBtn?.addEventListener("click", () => {
        createConversation({ activate: true });
        onNew();
        render();
        closeMobile();
    });

    return { render, closeMobile };
}
