import { exceedsApiWindow, MAX_API_MESSAGES } from "../utils/history.js";

/**
 * Aviso discreto quando o histórico visual excede a janela enviada ao modelo.
 * @param {HTMLElement | null} root
 */
export function createContextWindowNotice(root) {
    if (!root) {
        return { refresh() {} };
    }

    const message = `O assistente utiliza as últimas ${MAX_API_MESSAGES} mensagens como contexto ativo.`;

    function refresh(turnCount) {
        const show =
            typeof turnCount === "number"
                ? exceedsApiWindow(turnCount)
                : exceedsApiWindow();
        root.hidden = !show;
        if (show) {
            root.textContent = message;
        }
    }

    root.setAttribute("role", "status");
    root.setAttribute("aria-live", "polite");
    root.hidden = true;

    return { refresh };
}
