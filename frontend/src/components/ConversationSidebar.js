import { listConversations, switchConversation } from "../utils/conversations.js";
import { syncUrlState } from "../utils/deepLink.js";

const SIDEBAR_COLLAPSED_KEY = "kernel_sidebar_collapsed";

/**
 * @param {{
 *   sidebar: HTMLElement | null,
 *   listEl: HTMLElement | null,
 *   overlay: HTMLElement | null,
 *   toggleBtn: HTMLElement | null,
 *   newBtn: HTMLElement | null,
 *   searchInput: HTMLInputElement | null,
 *   collapseBtn: HTMLElement | null,
 *   getActiveId: () => string | null,
 *   onSelect: (id: string) => void,
 *   onNew: () => void,
 * }} opts
 */
export function createConversationSidebar(opts) {
    const {
        sidebar,
        listEl,
        overlay,
        toggleBtn,
        newBtn,
        searchInput,
        collapseBtn,
        getActiveId,
        onSelect,
        onNew,
    } = opts;

    /** @type {ReturnType<typeof setTimeout> | null} */
    let searchTimer = null;
    let searchQuery = "";

    function isDesktop() {
        return window.matchMedia("(min-width: 769px)").matches;
    }

    function loadCollapsed() {
        try {
            return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
        } catch {
            return false;
        }
    }

    function saveCollapsed(collapsed) {
        try {
            localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
        } catch {
            /* quota */
        }
    }

    function applyCollapsedState() {
        if (!sidebar || !isDesktop()) {
            sidebar?.classList.remove("conversation-sidebar--collapsed");
            return;
        }
        sidebar.classList.toggle("conversation-sidebar--collapsed", loadCollapsed());
        if (collapseBtn) {
            const collapsed = sidebar.classList.contains("conversation-sidebar--collapsed");
            collapseBtn.setAttribute("aria-expanded", collapsed ? "false" : "true");
            collapseBtn.setAttribute(
                "aria-label",
                collapsed ? "Expandir conversas" : "Recolher conversas",
            );
        }
    }

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
        const q = searchQuery.trim().toLowerCase();
        const items = listConversations().filter((conv) => {
            if (!q) return true;
            return (conv.title || "Nova conversa").toLowerCase().includes(q);
        });

        if (!items.length) {
            const empty = document.createElement("p");
            empty.className = "conversation-sidebar__empty";
            empty.textContent = q ? "Nenhuma conversa encontrada" : "Nenhuma conversa ainda";
            listEl.appendChild(empty);
            return;
        }

        for (const conv of items) {
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
                syncUrlState({ conversationId: conv.id });
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
        onNew();
        render();
        closeMobile();
    });

    collapseBtn?.addEventListener("click", () => {
        if (!sidebar || !isDesktop()) return;
        const next = !sidebar.classList.contains("conversation-sidebar--collapsed");
        sidebar.classList.toggle("conversation-sidebar--collapsed", next);
        saveCollapsed(next);
        applyCollapsedState();
    });

    searchInput?.addEventListener("input", () => {
        const value = searchInput.value;
        if (searchTimer) clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            searchQuery = value;
            render();
        }, 150);
    });

    window.addEventListener("resize", applyCollapsedState);
    applyCollapsedState();

    return { render, closeMobile, openMobile };
}
