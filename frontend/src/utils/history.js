export const SESSION_KEY = "acl_history";
export const MAX_HISTORY = 10;

export function loadHistory() {
    try {
        return JSON.parse(sessionStorage.getItem(SESSION_KEY) || "[]");
    } catch {
        return [];
    }
}

export function saveHistory(history) {
    try {
        sessionStorage.setItem(SESSION_KEY, JSON.stringify(history.slice(-MAX_HISTORY)));
    } catch {
        /* quota exceeded — ignora */
    }
}
