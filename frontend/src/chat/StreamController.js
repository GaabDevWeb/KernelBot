/**
 * Encapsula POST /chat SSE — delega a ChatService.sendStream.
 * @param {import('../api.js').ChatService} chatService
 */
export function createStreamController(chatService) {
    /** @type {AbortController | null} */
    let activeController = null;

    /**
     * @param {string} message
     * @param {string | undefined} sessionId
     * @param {Array<{ role: 'user' | 'assistant', content: string }>} history
     * @param {Parameters<import('../api.js').ChatService['sendStream']>[1]} handlers
     */
    async function send(message, sessionId, history, handlers) {
        activeController = new AbortController();
        try {
            return await chatService.sendStream(message, {
                sessionId,
                history,
                signal: activeController.signal,
                ...handlers,
            });
        } finally {
            activeController = null;
        }
    }

    function abort() {
        activeController?.abort();
    }

    return { send, abort };
}
