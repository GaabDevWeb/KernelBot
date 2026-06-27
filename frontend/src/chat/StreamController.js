/**
 * Encapsula POST /chat SSE — delega a ChatService.sendStream.
 * @param {import('../api.js').ChatService} chatService
 */
export function createStreamController(chatService) {
    /**
     * @param {string} message
     * @param {string | undefined} sessionId
     * @param {Array<{ role: 'user' | 'assistant', content: string }>} history
     * @param {Parameters<import('../api.js').ChatService['sendStream']>[1]} handlers
     */
    async function send(message, sessionId, history, handlers) {
        return chatService.sendStream(message, {
            sessionId,
            history,
            ...handlers,
        });
    }

    return { send };
}
