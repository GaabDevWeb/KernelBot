import {
    deleteConversation,
    listConversations,
    renameConversation,
    restoreConversation,
    switchConversation,
} from "../utils/conversations.js";
import { syncUrlState } from "../utils/deepLink.js";
import { showToast } from "../utils/toast.js";
import {
    refreshHeaderConversationLabelVisibility,
    updateHeaderConversationLabel,
} from "../utils/headerLabel.js";

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
 *   getActiveTitle: () => string,
 *   onSelect: (id: string) => void,
 *   onNew: () => void,
 *   onDeleteActive?: () => void,
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
        getActiveTitle,
        onSelect,
        onNew,
        onDeleteActive,
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

    function syncCollapsedBodyClass() {
        const collapsed =
            isDesktop() &&
            Boolean(sidebar?.classList.contains("conversation-sidebar--collapsed"));
        document.body.classList.toggle("sidebar-collapsed", collapsed);
        refreshHeaderConversationLabelVisibility();
    }

    function applyCollapsedState() {
        if (!sidebar || !isDesktop()) {
            sidebar?.classList.remove("conversation-sidebar--collapsed");
            syncCollapsedBodyClass();
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
        syncCollapsedBodyClass();
    }

    function closeMobile() {
        sidebar?.classList.remove("conversation-sidebar--open");
        overlay?.classList.remove("sidebar-overlay--visible");
    }

    function openMobile() {
        sidebar?.classList.add("conversation-sidebar--open");
        overlay?.classList.add("sidebar-overlay--visible");
    }

    function refreshHeaderLabel() {
        updateHeaderConversationLabel(getActiveTitle());
    }

    /**
     * @param {HTMLElement} item
     * @param {string} convId
     * @param {string} currentTitle
     */
    function startInlineRename(item, convId, currentTitle) {
        if (item.querySelector(".conversation-sidebar__rename-input")) return;

        const label = item.querySelector(".conversation-sidebar__item-label");
        if (!label) return;

        const input = document.createElement("input");
        input.type = "text";
        input.className = "conversation-sidebar__rename-input";
        input.value = currentTitle;
        input.setAttribute("aria-label", "Renomear conversa");
        label.replaceWith(input);
        input.focus();
        input.select();

        const commit = () => {
            const next = input.value.trim();
            if (next && next !== currentTitle) {
                renameConversation(convId, next);
                render();
                refreshHeaderLabel();
            } else {
                render();
            }
        };

        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                commit();
            }
            if (e.key === "Escape") {
                e.preventDefault();
                render();
            }
        });
        input.addEventListener("blur", commit);
    }

    /**
     * @param {HTMLElement} actionsEl
     * @param {string} convId
     */
    function showDeleteConfirm(actionsEl, convId) {
        actionsEl.replaceChildren();
        const confirm = document.createElement("span");
        confirm.className = "conversation-sidebar__confirm";
        confirm.textContent = "Excluir?";

        const yes = document.createElement("button");
        yes.type = "button";
        yes.className = "conversation-sidebar__confirm-yes";
        yes.textContent = "Sim";
        yes.addEventListener("click", (e) => {
            e.stopPropagation();
            performDelete(convId);
        });

        const no = document.createElement("button");
        no.type = "button";
        no.className = "conversation-sidebar__confirm-no";
        no.textContent = "Não";
        no.addEventListener("click", (e) => {
            e.stopPropagation();
            render();
        });

        actionsEl.append(confirm, yes, no);
    }

    /**
     * @param {string} convId
     */
    function performDelete(convId) {
        const previousActiveId = getActiveId();
        const index = listConversations().findIndex((c) => c.id === convId);
        const result = deleteConversation(convId);
        if (!result) return;

        showToast("Conversa excluída", {
            duration: 5000,
            actionLabel: "Desfazer",
            onAction: () => {
                restoreConversation(result.deleted, {
                    index,
                    activeId: previousActiveId,
                });
                if (result.wasActive) {
                    switchConversation(result.deleted.id);
                    syncUrlState({ conversationId: result.deleted.id });
                    onSelect(result.deleted.id);
                }
                render();
                refreshHeaderLabel();
            },
        });

        if (result.wasActive) {
            syncUrlState({ conversationId: result.nextActiveId });
            onDeleteActive?.();
        }
        render();
        refreshHeaderLabel();
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

        refreshHeaderLabel();

        if (!items.length) {
            const empty = document.createElement("p");
            empty.className = "conversation-sidebar__empty";
            empty.textContent = q ? "Nenhuma conversa encontrada" : "Nenhuma conversa ainda";
            listEl.appendChild(empty);
            return;
        }

        for (const conv of items) {
            const item = document.createElement("div");
            item.className = "conversation-sidebar__item-wrap";
            if (conv.id === activeId) item.classList.add("conversation-sidebar__item-wrap--active");

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "conversation-sidebar__item";
            btn.setAttribute("role", "listitem");
            if (conv.id === activeId) btn.classList.add("conversation-sidebar__item--active");

            const label = document.createElement("span");
            label.className = "conversation-sidebar__item-label";
            const title = conv.title || "Nova conversa";
            label.textContent = title;
            btn.title = title;
            btn.appendChild(label);

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

            btn.addEventListener("dblclick", (e) => {
                e.preventDefault();
                startInlineRename(item, conv.id, title);
            });

            const actions = document.createElement("div");
            actions.className = "conversation-sidebar__item-actions";

            const renameBtn = document.createElement("button");
            renameBtn.type = "button";
            renameBtn.className = "conversation-sidebar__action conversation-sidebar__action--rename";
            renameBtn.setAttribute("aria-label", "Renomear conversa");
            renameBtn.title = "Renomear";
            renameBtn.innerHTML =
                '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M11.5 2.5l2 2L5 13H3v-2L11.5 2.5z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>';
            renameBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                startInlineRename(item, conv.id, title);
            });

            const deleteBtn = document.createElement("button");
            deleteBtn.type = "button";
            deleteBtn.className = "conversation-sidebar__action conversation-sidebar__action--delete";
            deleteBtn.setAttribute("aria-label", "Excluir conversa");
            deleteBtn.title = "Excluir";
            deleteBtn.innerHTML =
                '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 4.5h10M6 4.5V3.5h4v1M5 4.5v8h6v-8" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>';
            deleteBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                showDeleteConfirm(actions, conv.id);
            });

            actions.append(renameBtn, deleteBtn);
            item.append(btn, actions);
            listEl.appendChild(item);
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

    return { render, closeMobile, openMobile, refreshHeaderLabel };
}
