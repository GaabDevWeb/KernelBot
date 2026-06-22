export function createStatusBadge(element) {
    return {
        setProcessing() {
            element.textContent = "Processando...";
            element.className = "header-badge";
        },
        setOnline() {
            element.textContent = "Online";
            element.className = "header-badge online";
        },
    };
}
