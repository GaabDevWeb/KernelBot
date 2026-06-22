/**
 * Cliente HTTP para POST /chat com corpo SSE (linhas `data: `, [DONE], [ERROR], [ACL_META]).
 */
export class ChatService {
    constructor(chatPath = "/chat") {
        this.chatPath = chatPath;
    }

    /**
     * Envia mensagem e consome o stream.
     * @param {string} message
     * @param {{ sessionId?: string, onDelta: (fullText: string) => void, onMeta?: (payload: Record<string, unknown>) => void, onFirstToken?: () => void }} handlers
     * @returns {Promise<{ ok: true, fullText: string, isError: boolean } | { ok: false, message: string }>}
     */
    async sendStream(message, { sessionId, onDelta, onMeta, onFirstToken }) {
        let fullText = "";
        let isError = false;
        let sawFirstToken = false;

        try {
            const body = { message };
            if (sessionId) {
                body.session_id = sessionId;
            }
            const res = await fetch(this.chatPath, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
                const detail =
                    typeof err.detail === "string"
                        ? err.detail
                        : Array.isArray(err.detail)
                          ? err.detail.map((d) => d.msg || d).join("; ")
                          : `HTTP ${res.status}`;
                return { ok: false, message: detail || `HTTP ${res.status}` };
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() ?? "";

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;
                    const payload = line.slice(6);

                    if (payload === "[DONE]") break;

                    if (payload.startsWith("[ERROR]")) {
                        isError = true;
                        fullText = payload.slice(8).trim();
                        onDelta?.(fullText);
                        break;
                    }

                    if (payload.startsWith("[ACL_META]")) {
                        const jsonPart = payload.slice("[ACL_META]".length);
                        try {
                            const meta = JSON.parse(jsonPart);
                            onMeta?.(meta);
                        } catch (e) {
                            console.warn("[ACL] ACL_META inválido:", e);
                        }
                        continue;
                    }

                    const beforeLen = fullText.length;
                    fullText += payload.replace(/\\n/g, "\n");
                    if (!sawFirstToken && fullText.length > beforeLen) {
                        sawFirstToken = true;
                        onFirstToken?.();
                    }
                    onDelta?.(fullText);
                }
            }

            return { ok: true, fullText, isError };
        } catch (err) {
            console.error("[ACL] Falha no stream:", err);
            return {
                ok: false,
                message: `Falha de conexão: ${err?.message || String(err)}`,
            };
        }
    }
}
