import { marked } from "../vendor/marked.esm.js";
import hljs from "../vendor/highlight.esm.js";
import { copyToClipboard } from "./clipboard.js";
import { decorateIssLessonLinks, linkifyFonteCitations } from "./issLinks.js";
import { showToast } from "./toast.js";

const DIAGRAM_LANGS = new Set(["mermaid", "graphviz", "dot", "flowchart", "diagram"]);
const DIAGRAM_CONTENT_RE =
    /[┌┐└┘│─├┤┬┴┼▼▲◄►→←↔]|\b(?:graph|flowchart)\s+(?:TD|TB|LR|RL|BT)\b/i;

/**
 * @param {string} code
 * @param {string | undefined} lang
 */
function isDiagramCode(code, lang) {
    const l = (lang || "").toLowerCase();
    if (DIAGRAM_LANGS.has(l)) return true;
    if (l && l !== "plaintext" && hljs.getLanguage(l)) return false;
    const c = (code || "").trim();
    if (!c) return false;
    return DIAGRAM_CONTENT_RE.test(c);
}

marked.setOptions({
    breaks: true,
    gfm: true,
    highlight(code, lang) {
        if (isDiagramCode(code, lang)) {
            return code
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");
        }
        const language = hljs.getLanguage(lang) ? lang : "plaintext";
        return hljs.highlight(code, { language }).value;
    },
});

const ACL_DISCLAIMER_RE =
    /não recebi trechos|\[fonte:/i;

/**
 * Parágrafos de disclaimer ACL / blocos [Fonte: …] → um único details colapsável por turno.
 * @param {ParentNode} root
 */
export function wrapAclDisclaimerBlocks(root) {
    if (!root) return;
    if (root.querySelector(".acl-disclaimer-collapsible")) return;

    /** @type {HTMLParagraphElement[]} */
    const matches = [];
    root.querySelectorAll("p").forEach((p) => {
        const text = (p.textContent || "").trim();
        if (!text || !ACL_DISCLAIMER_RE.test(text)) return;
        if (p.closest(".acl-disclaimer-collapsible")) return;
        matches.push(p);
    });
    if (!matches.length) return;

    const seen = new Set();
    /** @type {HTMLParagraphElement[]} */
    const unique = [];
    for (const p of matches) {
        const text = (p.textContent || "").trim();
        if (seen.has(text)) {
            p.remove();
            continue;
        }
        seen.add(text);
        unique.push(p);
    }
    if (!unique.length) return;

    const first = unique[0];
    const parent = first.parentNode;
    if (!parent) return;
    const insertBefore = first.nextSibling;

    const details = document.createElement("details");
    details.className = "acl-disclaimer-collapsible";

    const summary = document.createElement("summary");
    summary.className = "acl-disclaimer-collapsible__summary";
    summary.textContent = "Nota sobre fontes e contexto";

    const body = document.createElement("div");
    body.className = "acl-disclaimer-collapsible__body";
    for (const p of unique) {
        body.appendChild(p);
    }

    details.append(summary, body);
    parent.insertBefore(details, insertBefore);
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

/**
 * @param {ParentNode} root
 */
function applyCodeHighlighting(root) {
    if (!root) return;
    root.querySelectorAll("pre code").forEach((block) => {
        const pre = block.parentElement;
        const lang = [...block.classList]
            .find((c) => c.startsWith("language-"))
            ?.slice("language-".length);
        const code = block.textContent || "";

        if (isDiagramCode(code, lang)) {
            pre?.classList.add("code-block--diagram");
            block.className = "diagram-code";
            block.textContent = code;
            return;
        }

        hljs.highlightElement(block);
    });
}

/**
 * @param {string} text
 * @param {import('./issLinks.js').IssLinkContext} [issContext]
 */
export function renderMarkdown(text, issContext) {
    const linked = linkifyFonteCitations(text || "", issContext);
    const html = marked.parse(linked);
    const wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    applyCodeHighlighting(wrapper);
    decorateIssLessonLinks(wrapper);
    wrapAclDisclaimerBlocks(wrapper);
    attachCodeCopyButtons(wrapper);
    return wrapper.innerHTML;
}

export function highlightCodeBlocks(rootEl) {
    if (!rootEl) return;
    applyCodeHighlighting(rootEl);
    decorateIssLessonLinks(rootEl);
    wrapAclDisclaimerBlocks(rootEl);
    attachCodeCopyButtons(rootEl);
}
