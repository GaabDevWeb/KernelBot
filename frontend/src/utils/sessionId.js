const STORAGE_KEY = "acl_session_id";

/** @type {RegExp} */
const SID_PATTERN = /^[A-Za-z0-9_-]{8,128}$/;

/**
 * Identificador de sessão para contexto fixado no servidor (8–128 chars).
 * @returns {string}
 */
export function getOrCreateSessionId() {
    try {
        const existing = sessionStorage.getItem(STORAGE_KEY);
        if (existing && SID_PATTERN.test(existing)) {
            return existing;
        }
        const id = crypto.randomUUID().replace(/-/g, "");
        sessionStorage.setItem(STORAGE_KEY, id);
        return id;
    } catch {
        return "localfallback";
    }
}
