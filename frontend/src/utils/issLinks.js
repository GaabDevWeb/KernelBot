import { parseSourceParts } from "./formatSource.js";

let ISS_LESSON_BASE = "https://gaabdevweb.github.io/ISS/public/aula.html";

/**
 * @param {string} baseUrl
 */
export function setIssLessonBase(baseUrl) {
    const raw = String(baseUrl || "").trim();
    if (raw) ISS_LESSON_BASE = raw.replace(/\?+$/, "");
}

export function getIssLessonBase() {
    return ISS_LESSON_BASE;
}

/** @type {() => string | null} */
let resolveDisciplineId = () => null;

/**
 * @param {() => string | null} resolver
 */
export function setIssLinkDisciplineResolver(resolver) {
    resolveDisciplineId = typeof resolver === "function" ? resolver : () => null;
}

/**
 * @param {string} discipline
 * @param {string} slug
 * @returns {string | null}
 */
export function buildIssLessonUrl(discipline, slug) {
    const disc = sanitizeSegment(discipline);
    const les = sanitizeSlug(slug);
    if (!disc || !les) return null;
    const params = new URLSearchParams({ d: disc, a: les });
    return `${ISS_LESSON_BASE}?${params.toString()}`;
}

/**
 * @param {string} segment
 * @returns {string}
 */
function sanitizeSegment(segment) {
    const t = String(segment || "").trim().toLowerCase();
    if (!/^[a-z0-9][a-z0-9-]*$/.test(t)) return "";
    return t;
}

/**
 * @param {string} slug
 * @returns {string}
 */
function sanitizeSlug(slug) {
    const base = String(slug || "")
        .trim()
        .replace(/\.(json|md|txt)$/i, "");
    const leaf = base.split("/").filter(Boolean).pop() || base;
    return sanitizeSegment(leaf);
}

/**
 * @param {string} raw
 * @returns {{ discipline: string, slug: string, sourceKey: string } | null}
 */
export function parseCitationSource(raw) {
    const s = String(raw || "").trim();
    if (!s) return null;

    if (s.startsWith("db:")) {
        const path = s.slice(3).replace(/\\/g, "/");
        const parts = path.split("/").filter(Boolean);
        if (parts.length >= 2) {
            return {
                discipline: sanitizeSegment(parts[0]),
                slug: sanitizeSlug(parts.slice(1).join("/")),
                sourceKey: s.toLowerCase(),
            };
        }
        if (parts.length === 1) {
            return {
                discipline: "",
                slug: sanitizeSlug(parts[0]),
                sourceKey: s.toLowerCase(),
            };
        }
    }

    const segments = s.replace(/\\/g, "/").split("/").filter(Boolean);
    if (segments.length >= 2) {
        return {
            discipline: sanitizeSegment(segments[segments.length - 2]),
            slug: sanitizeSlug(segments[segments.length - 1]),
            sourceKey: s.toLowerCase(),
        };
    }

    return {
        discipline: "",
        slug: sanitizeSlug(s),
        sourceKey: s.toLowerCase(),
    };
}

/**
 * @param {Array<Record<string, unknown>> | undefined} sourceDetails
 * @returns {Map<string, { discipline: string, slug: string, lesson_title: string }>}
 */
export function buildSourceCatalog(sourceDetails) {
    /** @type {Map<string, { discipline: string, slug: string, lesson_title: string }>} */
    const map = new Map();
    if (!Array.isArray(sourceDetails)) return map;

    for (const detail of sourceDetails) {
        const discipline = sanitizeSegment(String(detail?.discipline || ""));
        const slug = sanitizeSlug(String(detail?.slug || ""));
        const lessonTitle = String(detail?.lesson_title || "").trim();
        const source = String(detail?.source || "").trim().toLowerCase();
        if (!slug && !source) continue;

        const entry = {
            discipline,
            slug,
            lesson_title: lessonTitle,
        };

        if (slug) map.set(slug, entry);
        if (source) map.set(source, entry);
        if (discipline && slug) map.set(`${discipline}/${slug}`, entry);
    }
    return map;
}

/**
 * @typedef {{ disciplineId?: string | null, sourceCatalog?: Map<string, { discipline: string, slug: string, lesson_title: string }> }} IssLinkContext
 */

/**
 * @param {{ sourceDetails?: Array<Record<string, unknown>>, disciplineId?: string | null }} [opts]
 * @returns {IssLinkContext}
 */
export function buildIssMarkdownContext(opts = {}) {
    const disciplineId =
        opts.disciplineId != null && String(opts.disciplineId).trim()
            ? sanitizeSegment(String(opts.disciplineId))
            : sanitizeSegment(resolveDisciplineId() || "") || null;

    return {
        disciplineId,
        sourceCatalog: buildSourceCatalog(opts.sourceDetails),
    };
}

/**
 * @param {{ discipline: string, slug: string, sourceKey: string }} parsed
 * @param {IssLinkContext} ctx
 * @returns {string}
 */
function resolveCitationTitle(parsed, ctx) {
    const catalog = ctx.sourceCatalog;
    if (catalog?.size) {
        const fromKey =
            catalog.get(parsed.sourceKey) ||
            (parsed.slug ? catalog.get(parsed.slug) : undefined) ||
            (parsed.discipline && parsed.slug
                ? catalog.get(`${parsed.discipline}/${parsed.slug}`)
                : undefined);
        if (fromKey?.lesson_title) return fromKey.lesson_title;
    }

    const parts = parseSourceParts(
        parsed.discipline && parsed.slug
            ? `db:${parsed.discipline}/${parsed.slug}`
            : parsed.slug || parsed.sourceKey,
    );
    if (parts?.lesson) return parts.lesson;
    if (parsed.slug) {
        const human = parseSourceParts(parsed.slug);
        return human?.lesson || parsed.slug;
    }
    return parsed.sourceKey;
}

/**
 * @param {string} text
 * @param {IssLinkContext} [ctx]
 * @returns {string}
 */
export function linkifyFonteCitations(text, ctx = {}) {
    const resolvedDiscipline =
        ctx.disciplineId != null && String(ctx.disciplineId).trim()
            ? ctx.disciplineId
            : sanitizeSegment(resolveDisciplineId() || "") || null;
    const context = {
        disciplineId: resolvedDiscipline,
        sourceCatalog: ctx.sourceCatalog ?? new Map(),
    };

    const FONTE_CITATION_RE =
        /\[Fonte(?:\s+(\d+))?:\s*([^\]|]+?)(?:\s*\|\s*Score:\s*[\d.]+)?\]/gi;

    return String(text || "").replace(FONTE_CITATION_RE, (full, num, sourceRaw) => {
        const parsed = parseCitationSource(String(sourceRaw || "").trim());
        if (!parsed?.slug) return full;

        let discipline = parsed.discipline;
        if (!discipline && context.sourceCatalog?.size) {
            const catalogHit =
                context.sourceCatalog.get(parsed.sourceKey) ||
                context.sourceCatalog.get(parsed.slug);
            discipline = catalogHit?.discipline || "";
        }
        if (!discipline) discipline = context.disciplineId || "";
        if (!discipline) return full;

        const url = buildIssLessonUrl(discipline, parsed.slug);
        if (!url) return full;

        const title = resolveCitationTitle(parsed, context);
        const prefix = num ? `Fonte ${num}` : "Fonte";
        return `[${prefix}: ${title}](${url})`;
    });
}

/**
 * @param {ParentNode} root
 */
export function decorateIssLessonLinks(root) {
    if (!root) return;
    root.querySelectorAll("a.iss-lesson-link").forEach((anchor) => {
        const el = /** @type {HTMLAnchorElement} */ (anchor);
        el.classList.add("iss-lesson-link");
        el.target = "_blank";
        el.rel = "noopener noreferrer";
        const label = (el.textContent || "").trim();
        if (label && !el.getAttribute("aria-label")) {
            el.setAttribute("aria-label", `Abrir aula no ISS: ${label.replace(/^Fonte(?:\s+\d+)?:\s*/i, "")}`);
        }
    });
}

/**
 * @param {string} discipline
 * @param {string} slug
 * @param {string} label
 * @returns {HTMLAnchorElement | null}
 */
export function createIssLessonAnchor(discipline, slug, label) {
    const href = buildIssLessonUrl(discipline, slug);
    if (!href) return null;

    const a = document.createElement("a");
    a.className = "iss-lesson-link source-card__title-link";
    a.href = href;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = label;
    a.setAttribute("aria-label", `Abrir aula no ISS: ${label}`);
    return a;
}
