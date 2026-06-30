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

/** @type {HTMLElement | null} */
let openMenuEl = null;

/**
 * @param {{
 *   sidebar: HTMLElement | null,
 *   listEl: HTMLElement | null,
 *   overlay: HTMLElement | null,
 *   toggleBtn: HTMLElement | null,
 *   newBtn: HTMLElement | null,
 *   searchInput: HTMLInputElement | null,
 *   searchToggleBtn: HTMLElement | null,
 *   collapseBtn: HTMLElement | null,
 *   logoBtn: HTMLElement | null,
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
        searchToggleBtn,
        collapseBtn,
        logoBtn,
        getActiveId,
        getActiveTitle,
        onSelect,
        onNew,
        onDeleteActive,
    } = opts;

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

    function isCollapsed() {
        return Boolean(sidebar?.classList.contains("conversation-sidebar--collapsed"));
    }

    function syncCollapsedBodyClass() {
        const collapsed = isDesktop() && isCollapsed();
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
            const collapsed = isCollapsed();
            collapseBtn.setAttribute("aria-expanded", collapsed ? "false" : "true");
            collapseBtn.setAttribute(
                "aria-label",
                collapsed ? "Expandir sidebar" : "Recolher sidebar",
            );
            collapseBtn.title = collapsed ? "Expandir sidebar" : "Recolher sidebar";
        }
        if (logoBtn) {
            const collapsed = isCollapsed();
            logoBtn.setAttribute(
                "aria-label",
                collapsed ? "Expandir barra lateral" : "Nova conversa",
            );
            logoBtn.title = collapsed ? "Expandir barra lateral" : "Nova conversa";
        }
        syncCollapsedBodyClass();
    }

    function expandSidebar() {
        if (!sidebar || !isDesktop()) return;
        sidebar.classList.remove("conversation-sidebar--collapsed");
        saveCollapsed(false);
        applyCollapsedState();
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

    function closeAllMenus() {
        if (!openMenuEl) return;
        openMenuEl.hidden = true;
        openMenuEl
            .closest(".conversation-sidebar__menu-wrap")
            ?.querySelector(".conversation-sidebar__menu-trigger")
            ?.setAttribute("aria-expanded", "false");
        openMenuEl = null;
    }

    /**
     * @param {HTMLElement} menuEl
     * @param {HTMLButtonElement} trigger
     * @param {HTMLButtonElement[]} menuItems
     */
    function bindMenuKeyboard(menuEl, trigger, menuItems) {
        /**
         * @param {KeyboardEvent} e
         */
        function onMenuKeydown(e) {
            if (menuEl.hidden) return;

            const items = menuItems.filter((el) => el.isConnected && !el.hidden);
            if (!items.length) return;

            const active = document.activeElement;
            let index = items.indexOf(/** @type {HTMLButtonElement} */ (active));

            if (e.key === "ArrowDown") {
                e.preventDefault();
                index = index < 0 ? 0 : (index + 1) % items.length;
                items[index]?.focus();
                return;
            }
            if (e.key === "ArrowUp") {
                e.preventDefault();
                index = index < 0 ? items.length - 1 : (index - 1 + items.length) % items.length;
                items[index]?.focus();
                return;
            }
            if (e.key === "Home") {
                e.preventDefault();
                items[0]?.focus();
                return;
            }
            if (e.key === "End") {
                e.preventDefault();
                items[items.length - 1]?.focus();
                return;
            }
            if (e.key === "Escape") {
                e.preventDefault();
                closeAllMenus();
                trigger.focus();
            }
        }

        menuEl.addEventListener("keydown", onMenuKeydown);
    }

    /**
     * @param {HTMLElement} menuEl
     * @param {HTMLButtonElement} trigger
     */
    function openMenu(menuEl, trigger) {
        closeAllMenus();
        menuEl.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
        openMenuEl = menuEl;
        const first = menuEl.querySelector('[role="menuitem"]');
        first?.focus();
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

        closeAllMenus();

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
     * @param {HTMLElement} menuEl
     * @param {string} convId
     */
    function showDeleteConfirmInMenu(menuEl, convId) {
        menuEl.replaceChildren();
        const text = document.createElement("p");
        text.className = "conversation-sidebar__menu-confirm";
        text.textContent = "Excluir conversa?";

        const actions = document.createElement("div");
        actions.className = "conversation-sidebar__menu-confirm-actions";

        const yes = document.createElement("button");
        yes.type = "button";
        yes.className = "conversation-sidebar__menu-confirm-yes";
        yes.textContent = "Sim";
        yes.addEventListener("click", (e) => {
            e.stopPropagation();
            closeAllMenus();
            performDelete(convId);
        });

        const no = document.createElement("button");
        no.type = "button";
        no.textContent = "Não";
        no.addEventListener("click", (e) => {
            e.stopPropagation();
            closeAllMenus();
            render();
        });

        actions.append(yes, no);
        menuEl.append(text, actions);
        yes.focus();
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

    /**
     * @param {HTMLElement} wrap
     * @param {string} convId
     * @param {string} title
     */
    function buildContextMenu(wrap, convId, title) {
        const menuWrap = document.createElement("div");
        menuWrap.className = "conversation-sidebar__menu-wrap";

        const trigger = document.createElement("button");
        trigger.type = "button";
        trigger.className = "conversation-sidebar__menu-trigger";
        trigger.setAttribute("aria-label", "Ações da conversa");
        trigger.setAttribute("aria-haspopup", "menu");
        trigger.setAttribute("aria-expanded", "false");
        trigger.textContent = "…";

        const menu = document.createElement("div");
        menu.className = "conversation-sidebar__menu";
        menu.setAttribute("role", "menu");
        menu.hidden = true;

        const renameItem = document.createElement("button");
        renameItem.type = "button";
        renameItem.className = "conversation-sidebar__menu-item";
        renameItem.setAttribute("role", "menuitem");
        renameItem.textContent = "Renomear";
        renameItem.addEventListener("click", (e) => {
            e.stopPropagation();
            closeAllMenus();
            startInlineRename(wrap, convId, title);
        });

        const deleteItem = document.createElement("button");
        deleteItem.type = "button";
        deleteItem.className = "conversation-sidebar__menu-item conversation-sidebar__menu-item--danger";
        deleteItem.setAttribute("role", "menuitem");
        deleteItem.textContent = "Excluir";
        deleteItem.addEventListener("click", (e) => {
            e.stopPropagation();
            showDeleteConfirmInMenu(menu, convId);
        });

        menu.append(renameItem, deleteItem);
        bindMenuKeyboard(menu, trigger, [renameItem, deleteItem]);

        function toggleMenu() {
            if (menu.hidden) {
                menu.replaceChildren(renameItem, deleteItem);
                openMenu(menu, trigger);
            } else {
                closeAllMenus();
            }
        }

        trigger.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleMenu();
        });

        trigger.addEventListener("keydown", (e) => {
            if (e.key !== "Enter" && e.key !== " ") return;
            e.preventDefault();
            toggleMenu();
        });

        menuWrap.append(trigger, menu);
        return menuWrap;
    }

    /**
     * @param {string} title
     */
    function conversationInitial(title) {
        const trimmed = (title || "N").trim();
        return trimmed.charAt(0).toUpperCase();
    }

    function selectConversation(convId) {
        if (convId === getActiveId()) {
            closeMobile();
            return;
        }
        switchConversation(convId);
        syncUrlState({ conversationId: convId });
        onSelect(convId);
        render();
        closeMobile();
    }

    function refreshHeaderLabel() {
        updateHeaderConversationLabel(getActiveTitle());
    }

    function updateListScrollAffordance() {
        if (!listEl) return;
        const overflow = listEl.scrollHeight > listEl.clientHeight + 2;
        listEl.classList.toggle("conversation-sidebar__list--overflow", overflow);
        if (!overflow) {
            listEl.classList.remove(
                "conversation-sidebar__list--at-top",
                "conversation-sidebar__list--at-bottom",
            );
            return;
        }
        const atTop = listEl.scrollTop <= 2;
        const atBottom =
            listEl.scrollTop + listEl.clientHeight >= listEl.scrollHeight - 2;
        listEl.classList.toggle("conversation-sidebar__list--at-top", atTop);
        listEl.classList.toggle("conversation-sidebar__list--at-bottom", atBottom);
    }

    function render() {
        if (!listEl) return;
        listEl.replaceChildren();
        closeAllMenus();

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
            requestAnimationFrame(updateListScrollAffordance);
            return;
        }

        for (const conv of items) {
            const title = conv.title || "Nova conversa";
            const wrap = document.createElement("div");
            wrap.className = "conversation-sidebar__item-wrap";
            if (conv.id === activeId) wrap.classList.add("conversation-sidebar__item-wrap--active");

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "conversation-sidebar__item";
            btn.setAttribute("role", "listitem");
            if (conv.id === activeId) btn.classList.add("conversation-sidebar__item--active");

            const label = document.createElement("span");
            label.className = "conversation-sidebar__item-label";
            label.textContent = title;
            btn.title = title;
            btn.appendChild(label);

            btn.addEventListener("click", () => selectConversation(conv.id));
            btn.addEventListener("dblclick", (e) => {
                e.preventDefault();
                startInlineRename(wrap, conv.id, title);
            });

            const initialBtn = document.createElement("button");
            initialBtn.type = "button";
            initialBtn.className = "conversation-sidebar__item-initial";
            initialBtn.textContent = conversationInitial(title);
            initialBtn.title = title;
            initialBtn.setAttribute("aria-label", title);
            initialBtn.addEventListener("click", () => selectConversation(conv.id));

            wrap.append(btn, initialBtn, buildContextMenu(wrap, conv.id, title));
            listEl.appendChild(wrap);
        }

        requestAnimationFrame(updateListScrollAffordance);
    }

    function startNewChat() {
        onNew();
        render();
        closeMobile();
    }

    toggleBtn?.addEventListener("click", () => {
        if (sidebar?.classList.contains("conversation-sidebar--open")) closeMobile();
        else openMobile();
    });

    overlay?.addEventListener("click", closeMobile);

    newBtn?.addEventListener("click", startNewChat);

    collapseBtn?.addEventListener("click", () => {
        if (!sidebar || !isDesktop()) return;
        const next = !isCollapsed();
        sidebar.classList.toggle("conversation-sidebar--collapsed", next);
        saveCollapsed(next);
        applyCollapsedState();
        if (!next) searchInput?.focus();
    });

    logoBtn?.addEventListener("click", () => {
        if (!sidebar) return;
        if (isDesktop() && isCollapsed()) {
            expandSidebar();
            return;
        }
        startNewChat();
    });

    searchToggleBtn?.addEventListener("click", () => {
        expandSidebar();
        window.setTimeout(() => searchInput?.focus(), 240);
    });

    searchInput?.addEventListener("focus", () => {
        expandSidebar();
    });

    searchInput?.addEventListener("input", () => {
        searchQuery = searchInput.value;
        if (searchQuery.trim()) expandSidebar();
        render();
    });

    document.addEventListener("click", (e) => {
        if (!(e.target instanceof Node)) return;
        if (
            openMenuEl &&
            !openMenuEl.contains(e.target) &&
            !e.target.closest(".conversation-sidebar__menu-trigger")
        ) {
            closeAllMenus();
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeAllMenus();
    });

    window.addEventListener("resize", applyCollapsedState);
    applyCollapsedState();

    if (listEl) {
        listEl.addEventListener("scroll", updateListScrollAffordance, { passive: true });
        new ResizeObserver(() => updateListScrollAffordance()).observe(listEl);
    }

    newBtn?.setAttribute("title", "Nova conversa");
    searchToggleBtn?.setAttribute("title", "Pesquisar chats");

    return { render, closeMobile, openMobile, refreshHeaderLabel };
}
