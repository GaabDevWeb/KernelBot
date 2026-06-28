import { marked } from "https://cdn.jsdelivr.net/npm/marked@12/+esm";
import hljs from "https://esm.sh/highlight.js@11.9.0";
import { copyToClipboard } from "./clipboard.js";
import { showToast } from "./toast.js";

marked.setOptions({
    breaks: true,
    gfm: true,
    highlight(code, lang) {
        const language = hljs.getLanguage(lang) ? lang : "plaintext";
        return hljs.highlight(code, { language }).value;
    },
});

const ACL_DISCLAIMER_RE =
    /não recebi trechos|\[fonte:/i;

/**
 * Parágrafos de disclaimer ACL / blocos [Fonte: …] → details colapsável.
 * @param {ParentNode} root
 */
export function wrapAclDisclaimerBlocks(root) {
    if (!root) return;
    root.querySelectorAll("p").forEach((p) => {
        const text = (p.textContent || "").trim();
        if (!text || !ACL_DISCLAIMER_RE.test(text)) return;
        if (p.closest(".acl-disclaimer-collapsible")) return;

        const details = document.createElement("details");
        details.className = "acl-disclaimer-collapsible";

        const summary = document.createElement("summary");
        summary.className = "acl-disclaimer-collapsible__summary";
        summary.textContent = "Nota sobre fontes e contexto";

        const body = document.createElement("div");
        body.className = "acl-disclaimer-collapsible__body";
        body.appendChild(p.cloneNode(true));

        details.append(summary, body);
        p.replaceWith(details);
    });
}

/**
 * @param {ParentNode} root
 */
export function attachCodeCopyButtons(root) {
    if (!root) return;
    root.querySelectorAll("pre").forEach((pre) => {
        if (pre.querySelector(".code-copy-btn")) return;

        const wrap = document.createElement("div");
        wrap.className = "code-block-wrap";
        pre.parentNode?.insertBefore(wrap, pre);
        wrap.appendChild(pre);

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "code-copy-btn";
        btn.setAttribute("aria-label", "Copiar código");
        btn.title = "Copiar";
        btn.textContent = "Copiar";
        btn.addEventListener("click", async () => {
            const code = pre.querySelector("code");
            const text = code?.textContent || pre.textContent || "";
            const ok = await copyToClipboard(text);
            showToast(ok ? "Código copiado" : "Não foi possível copiar");
        });
        wrap.appendChild(btn);
    });
}

export function renderMarkdown(text) {
    const html = marked.parse(text || "");
    const wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    wrapper.querySelectorAll("pre code").forEach((block) => {
        hljs.highlightElement(block);
    });
    wrapAclDisclaimerBlocks(wrapper);
    attachCodeCopyButtons(wrapper);
    return wrapper.innerHTML;
}

export function highlightCodeBlocks(rootEl) {
    if (!rootEl) return;
    rootEl.querySelectorAll("pre code").forEach((block) => {
        hljs.highlightElement(block);
    });
    wrapAclDisclaimerBlocks(rootEl);
    attachCodeCopyButtons(rootEl);
}
