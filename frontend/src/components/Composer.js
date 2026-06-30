/**
 * @param {{ input: HTMLTextAreaElement, sendButton: HTMLButtonElement, onSend: () => void | Promise<void>, onStop?: () => void, maxHeightPx?: number, pillsRoot?: ParentNode }} opts
 */
export function createComposer({
    input,
    sendButton,
    onSend,
    onStop,
    maxHeightPx = 140,
    pillsRoot = document,
}) {
    let streaming = false;
    const defaultSendLabel = sendButton.getAttribute("aria-label") || "Enviar mensagem";
    const defaultSendTitle = sendButton.getAttribute("title") || "Enviar (Enter)";

    function autoResize() {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, maxHeightPx) + "px";
    }

    input.addEventListener("input", autoResize);
    sendButton.addEventListener("click", () => {
        if (streaming) {
            onStop?.();
            return;
        }
        void onSend();
    });
    input.addEventListener("keydown", (e) => {
        const slashMenu = document.getElementById("slash-command-menu");
        if (slashMenu && !slashMenu.hidden) return;
        if (streaming) return;
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            void onSend();
        }
    });

    pillsRoot.querySelectorAll(".cmd-pill").forEach((pill) => {
        pill.addEventListener("click", () => {
            const cmd = pill.dataset.cmd || pill.textContent || "";
            input.value = cmd.endsWith(" ") ? cmd : `${cmd.trim()} `;
            input.dispatchEvent(new Event("input"));
            requestAnimationFrame(() => input.focus());
        });
    });

    return {
        focus() {
            input.focus();
        },
        setEnabled(enabled) {
            sendButton.disabled = !enabled && !streaming;
        },
        setStreaming(active) {
            streaming = Boolean(active);
            sendButton.disabled = false;
            sendButton.classList.toggle("send-button--streaming", streaming);
            input.classList.toggle("composer-input--streaming", streaming);
            input.setAttribute("aria-busy", streaming ? "true" : "false");
            sendButton.setAttribute(
                "aria-label",
                streaming ? "Parar geração" : defaultSendLabel,
            );
            sendButton.setAttribute(
                "title",
                streaming ? "Parar geração" : defaultSendTitle,
            );
        },
        isStreaming() {
            return streaming;
        },
        clear() {
            input.value = "";
            input.style.height = "auto";
        },
        getValueTrimmed() {
            return input.value.trim();
        },
    };
}
