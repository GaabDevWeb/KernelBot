import { ChatService } from "./api.js";
import { buildDisambiguationFollowUp } from "./acl/parseAclMeta.js";
import { createComposerController } from "./chat/ComposerController.js";
import { createMetaRenderer } from "./chat/MetaRenderer.js";
import { createStreamController } from "./chat/StreamController.js";
import { createTurnController } from "./chat/TurnController.js";
import { restoreSessionPinFromHistory } from "./chat/restoreTurn.js";
import { createSlashCommandMenu } from "./components/SlashCommandMenu.js";
import { createConversationSidebar } from "./components/ConversationSidebar.js";
import { createContextWindowNotice } from "./components/ContextWindowNotice.js";
import { createComposer } from "./components/Composer.js";
import { createChatView } from "./components/ChatView.js";
import { createDisciplinePanel } from "./components/DisciplinePanel.js";
import { createStatusBadge } from "./components/StatusBadge.js";
import {
    getHistoryForApi,
    loadConversation,
    loadHistory,
    saveHistory,
} from "./utils/history.js";
import {
    createConversation,
    getActiveConversation,
    getConversationDiscipline,
    setConversationDiscipline,
} from "./utils/conversations.js";
import {
    applyConversationDeepLink,
    applyDisciplineDeepLink,
    syncDisciplineQueryParam,
    syncUrlState,
} from "./utils/deepLink.js";
import { rebuildProgressFromHistory } from "./utils/progress.js";
import { getOrCreateSessionId, regenerateSessionId } from "./utils/sessionId.js";
import { renderMarkdown } from "./utils/markdown.js";
import { syncBodyUiState } from "./utils/uiState.js";
import { initShortcutsOverlay } from "./components/ShortcutsOverlay.js";
import {
    refreshHeaderConversationLabelVisibility,
    updateHeaderConversationLabel,
} from "./utils/headerLabel.js";

export function init() {
    const chatBox = document.getElementById("chat");
    const input = /** @type {HTMLTextAreaElement | null} */ (document.getElementById("message-input"));
    const sendBtn = document.getElementById("send-button");
    const emptyState = document.getElementById("empty-state");
    const statusBadge = document.getElementById("status-badge");
    const inputArea = document.querySelector(".input-area");
    const siloPill = document.getElementById("silo-pill");
    const pinBadge = document.getElementById("context-pin-badge");
    const contextStack = document.getElementById("context-stack");
    const activeDisciplineBadge = document.getElementById("active-discipline-badge");
    const scopeBtn = document.getElementById("scope-btn");
    const contextWindowNoticeEl = document.getElementById("context-window-notice");
    const composerWrap = document.getElementById("composer-wrap");
    const sidebarEl = document.getElementById("conversation-sidebar");
    const conversationList = document.getElementById("conversation-list");
    const sidebarOverlay = document.getElementById("sidebar-overlay");
    const sidebarToggle = document.getElementById("sidebar-toggle");
    const sidebarNewBtn = document.getElementById("sidebar-new-chat");
    const sidebarSearch = /** @type {HTMLInputElement | null} */ (
        document.getElementById("sidebar-search")
    );
    const sidebarSearchToggle = document.getElementById("sidebar-search-toggle");
    const sidebarCollapseBtn = document.getElementById("sidebar-collapse-toggle");
    const sidebarLogoBtn = document.getElementById("sidebar-logo-btn");

    let sessionId = getOrCreateSessionId();

    if (!chatBox || !input || !sendBtn || !statusBadge) {
        console.error("[ACL] DOM esperado ausente (chat, input, send ou status).");
        return;
    }

    const chatService = new ChatService();
    const streamController = createStreamController(chatService);
    const status = createStatusBadge(statusBadge);
    const contextWindowNotice = createContextWindowNotice(contextWindowNoticeEl);

    function refreshContextWindowNotice(turnCount) {
        contextWindowNotice.refresh(turnCount);
    }

    function refreshContextStack() {
        if (!contextStack) return;
        const siloVisible = siloPill && !siloPill.hidden;
        const pinVisible = pinBadge && !pinBadge.hidden;
        contextStack.hidden = !(siloVisible || pinVisible);
    }

    const metaRenderer = createMetaRenderer({ pinBadge, contextStack, refreshContextStack });
    const { refreshPinBadge, hidePinBadge } = metaRenderer;

    const { refreshSiloUi, getActiveDisciplineId } = createComposerController({
        input,
        inputArea,
        siloPill,
        activeDisciplineBadge,
        scopeBtn,
        contextStack,
        refreshContextStack,
        hidePinBadge,
        onDisciplineChange: syncDisciplineQueryParam,
        getStoredDisciplineId: () => getConversationDiscipline(getActiveConversation().id),
        setStoredDisciplineId: (disciplineId) =>
            setConversationDiscipline(getActiveConversation().id, disciplineId),
    });

    /** @type {ReturnType<typeof createTurnController> | null} */
    let turnController = null;

    function pinFromSource(detail) {
        const followUp = buildDisambiguationFollowUp({
            discipline: String(detail?.discipline || ""),
            slug: String(detail?.slug || ""),
            title: String(detail?.lesson_title || ""),
        });
        input.value = followUp;
        input.dispatchEvent(new Event("input"));
        refreshSiloUi();
        if (turnController?.queueFollowUp(followUp)) return;
        void turnController?.send(followUp);
    }

    const sourceHandlers = { onPinSource: pinFromSource };

    function chipSelectFromRestore(candidate) {
        const followUp = buildDisambiguationFollowUp(candidate);
        input.value = followUp;
        input.dispatchEvent(new Event("input"));
        refreshSiloUi();
        if (turnController?.queueFollowUp(followUp)) return;
        void turnController?.send(followUp);
    }

    const chipHandlers = { onSelect: chipSelectFromRestore };

    const chatView = createChatView({
        chatBox,
        emptyState,
        renderMarkdown,
        sourceHandlers,
        chipHandlers,
        onRegenerate: () => void turnController?.regenerateLast(),
    });

    /** @type {ReturnType<typeof createComposer>} */
    let composer;

    /** @type {ReturnType<typeof createConversationSidebar> | null} */
    let sidebar = null;

    /** @type {ReturnType<typeof createDisciplinePanel> | null} */
    let disciplinePanel = null;

    function restorePinFromActiveConversation() {
        const turns = loadConversation().turns;
        restoreSessionPinFromHistory(turns, refreshPinBadge, hidePinBadge);
    }

    function bootstrapConversationView() {
        const turns = loadHistory();
        rebuildProgressFromHistory(turns);
        if (turns.length) {
            chatView.renderSavedHistory(turns);
            window.__kernelGlobe?.dismiss(0);
        }
        refreshContextWindowNotice(loadConversation().turns.length);
        restorePinFromActiveConversation();
        refreshSiloUi();
        syncUrlState({
            conversationId: getActiveConversation().id,
            disciplineId: getActiveDisciplineId(),
        });
        updateHeaderConversationLabel(getActiveConversation().title);
        disciplinePanel?.refresh();
        syncBodyUiState();
    }

    function reloadConversationView() {
        sessionId = getOrCreateSessionId();
        chatView.clearChat();
        bootstrapConversationView();
        sidebar?.render();
        updateHeaderConversationLabel(getActiveConversation().title);
    }

    function finishConversationReset() {
        createConversation({ activate: true });
        sessionId = regenerateSessionId();
        chatView.clearChat();
        chatView.showLanding();
        input.value = "";
        input.dispatchEvent(new Event("input"));
        hidePinBadge();
        refreshSiloUi();
        refreshContextWindowNotice(0);
        sidebar?.render();
        syncUrlState({
            conversationId: getActiveConversation().id,
            disciplineId: getActiveDisciplineId(),
        });
        updateHeaderConversationLabel(getActiveConversation().title);
        syncBodyUiState();
        composer.focus();
    }

    composer = createComposer({
        input,
        sendButton: sendBtn,
        onSend: () => void turnController?.send(),
        onStop: () => turnController?.abortStream(),
        pillsRoot: document,
    });

    turnController = createTurnController({
        chatBox,
        input,
        chatView,
        streamController,
        composer,
        status,
        metaRenderer,
        sourceHandlers,
        refreshSiloUi,
        getSessionId: () => sessionId,
        getHistoryForApi,
        loadHistory,
        saveHistory,
        onConversationReset: finishConversationReset,
        refreshContextWindowNotice,
    });

    if (composerWrap) {
        createSlashCommandMenu(input, composerWrap);
    }

    disciplinePanel = createDisciplinePanel({
        input,
        refreshSiloUi,
        getDisciplineId: getActiveDisciplineId,
        scopeBtn,
        siloPill,
    });

    sidebar = createConversationSidebar({
        sidebar: sidebarEl,
        listEl: conversationList,
        overlay: sidebarOverlay,
        toggleBtn: sidebarToggle,
        newBtn: sidebarNewBtn,
        searchInput: sidebarSearch,
        searchToggleBtn: sidebarSearchToggle,
        collapseBtn: sidebarCollapseBtn,
        logoBtn: sidebarLogoBtn,
        getActiveId: () => getActiveConversation().id,
        getActiveTitle: () => getActiveConversation().title || "Nova conversa",
        onSelect: () => reloadConversationView(),
        onNew: () => finishConversationReset(),
        onDeleteActive: () => reloadConversationView(),
    });

    initShortcutsOverlay();

    applyDisciplineDeepLink(input, () => {
        refreshSiloUi();
        disciplinePanel?.refresh();
    });
    const deepLinked = applyConversationDeepLink(() => reloadConversationView());

    input.addEventListener("input", refreshSiloUi);
    window.addEventListener("kernel:chat-active", () => {
        refreshSiloUi();
        refreshHeaderConversationLabelVisibility();
    });
    refreshSiloUi();
    refreshContextStack();

    if (!deepLinked) {
        bootstrapConversationView();
    }
    sidebar.render();
    updateHeaderConversationLabel(getActiveConversation().title);
    composer.focus();
}
