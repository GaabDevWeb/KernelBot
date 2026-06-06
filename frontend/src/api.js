/**
 * Cliente HTTP para POST /chat com corpo SSE (linhas `data: `, [DONE], [ERROR], [ACL_META]).
 *
 * Falha de parse em `[ACL_META]`: acumula fragmento JSON até parse válido; o stream de texto continua.
 * Inatividade: se não chegar token/meta durante `inactivityMs`, aborta (rede pendurada ≠ Offline instantâneo).
 */

/** Pausa máxima sem bytes SSE antes de encerrar o turno (ms). */
export const DEFAULT_STREAM_INACTIVITY_MS = 45_000;

export class ChatService {
    constructor(chatPath = "/chat") {
        this.chatPath = chatPath;
    }

    /**
     * @param {string} jsonPart
     * @param {string} aclMetaBuffer
     * @returns {{ meta: Record<string, unknown> | null, buffer: string }}
     */
    _tryParseAclMeta(jsonPart, aclMetaBuffer) {
        const combined = aclMetaBuffer + jsonPart;
        try {
            return { meta: JSON.parse(combined), buffer: "" };
        } catch {
            if (/^\s*[\{\[]/.test(combined) && combined.length < 65536) {
                return { meta: null, buffer: combined };
            }
            console.error("ACL_META Parse failed — descartando buffer", combined.slice(0, 120));
            return { meta: null, buffer: "" };
        }
    }

    /**
     * Envia mensagem e consome o stream.
     * @param {string} message
     * @param {{
     *   sessionId?: string,
     *   history?: Array<{ role: 'user' | 'assistant', content: string }>,
     *   inactivityMs?: number,
     *   onDelta: (fullText: string) => void,
     *   onMeta?: (payload: Record<string, unknown>) => void,
     *   onFirstToken?: () => void,
     *   onAbort?: () => void,
     *   onInactivity?: () => void,
     * }} handlers
     * @returns {Promise<
     *   | { ok: true, fullText: string, isError: boolean, aborted?: boolean, stalled?: boolean }
     *   | { ok: false, message: string, aborted?: boolean, stalled?: boolean }
     * >}
     */
    async sendStream(message, handlers) {
        const {
            sessionId,
            history,
            onDelta,
            onMeta,
            onFirstToken,
            onAbort,
            onInactivity,
            inactivityMs = DEFAULT_STREAM_INACTIVITY_MS,
        } = handlers;

        let fullText = "";
        let isError = false;
        let sawFirstToken = false;
        let aclMetaBuffer = "";
        let aborted = false;
        let stalledByInactivity = false;

        const controller = new AbortController();
        /** @type {ReturnType<typeof setTimeout> | undefined} */
        let inactivityTimer;

        const clearInactivityTimer = () => {
            if (inactivityTimer !== undefined) {
                clearTimeout(inactivityTimer);
                inactivityTimer = undefined;
            }
        };

        const bumpInactivity = () => {
            clearInactivityTimer();
            if (inactivityMs <= 0) return;
            inactivityTimer = setTimeout(() => {
                stalledByInactivity = true;
                controller.abort();
            }, inactivityMs);
        };

        try {
            const body = { message };
            if (sessionId) {
                body.session_id = sessionId;
            }
            if (Array.isArray(history) && history.length) {
                body.history = history;
            }
            bumpInactivity();

            const res = await fetch(this.chatPath, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
                signal: controller.signal,
            });

            if (!res.ok) {
                clearInactivityTimer();
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

                bumpInactivity();
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
                        bumpInactivity();
                        const jsonPart = payload.slice("[ACL_META]".length);
                        const { meta, buffer: nextBuf } = this._tryParseAclMeta(
                            jsonPart,
                            aclMetaBuffer,
                        );
                        aclMetaBuffer = nextBuf;
                        if (meta) {
                            onMeta?.(meta);
                        }
                        continue;
                    }

                    const beforeLen = fullText.length;
                    fullText += payload.replace(/\\n/g, "\n");
                    if (!sawFirstToken && fullText.length > beforeLen) {
                        sawFirstToken = true;
                        onFirstToken?.();
                    }
                    bumpInactivity();
                    onDelta?.(fullText);
                }
            }

            clearInactivityTimer();
            return { ok: true, fullText, isError };
        } catch (err) {
            clearInactivityTimer();
            if (err?.name === "AbortError") {
                if (stalledByInactivity) {
                    onInactivity?.();
                    return {
                        ok: false,
                        message:
                            "O stream parou de enviar dados (timeout de inatividade). Verifique a rede e tente de novo.",
                        stalled: true,
                    };
                }
                aborted = true;
                onAbort?.();
                return { ok: false, message: "Stream cancelado.", aborted: true };
            }
            console.error("[ACL] Falha no stream:", err);
            return {
                ok: false,
                message: `Falha de conexão: ${err?.message || String(err)}`,
            };
        }
    }
}
