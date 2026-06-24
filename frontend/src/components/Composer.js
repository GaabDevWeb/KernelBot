/**
 * @param {{ input: HTMLTextAreaElement, sendButton: HTMLButtonElement, onSend: () => void | Promise<void>, maxHeightPx?: number, pillsRoot?: ParentNode }} opts
 */
export function createComposer({
    input,
    sendButton,
    onSend,
    maxHeightPx = 140,
    pillsRoot = document,
}) {
    function autoResize() {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, maxHeightPx) + "px";
    }

    input.addEventListener("input", autoResize);
    sendButton.addEventListener("click", () => {
        void onSend();
    });
    input.addEventListener("keydown", (e) => {
        const slashMenu = document.getElementById("slash-command-menu");
        if (slashMenu && !slashMenu.hidden) return;
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
            input.focus();
        });
    });

    return {
        focus() {
            input.focus();
        },
        setEnabled(enabled) {
            sendButton.disabled = !enabled;
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
