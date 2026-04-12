import { marked } from "https://cdn.jsdelivr.net/npm/marked@12/+esm";
import hljs from "https://esm.sh/highlight.js@11.9.0";

marked.setOptions({
    breaks: true,
    gfm: true,
    highlight(code, lang) {
        const language = hljs.getLanguage(lang) ? lang : "plaintext";
        return hljs.highlight(code, { language }).value;
    },
});

export function renderMarkdown(text) {
    const html = marked.parse(text || "");
    const wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    wrapper.querySelectorAll("pre code").forEach((block) => {
        hljs.highlightElement(block);
    });
    return wrapper.innerHTML;
}

export function highlightCodeBlocks(rootEl) {
    if (!rootEl) return;
    rootEl.querySelectorAll("pre code").forEach((block) => {
        hljs.highlightElement(block);
    });
}
