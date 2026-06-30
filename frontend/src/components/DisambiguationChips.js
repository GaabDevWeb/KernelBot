/**
 * Chips de desambiguação a partir de `suggested_candidates`.
 */

/**
 * @param {unknown} raw
 * @returns {{ title: string, discipline: string, slug: string } | null}
 */
function normalizeCandidate(raw) {
    if (!raw || typeof raw !== "object") return null;
    const title = String(raw.title || raw.slug || "Aula").trim();
    const discipline = String(raw.discipline || "").trim();
    const slug = String(raw.slug || "").trim();
    if (!title && !slug) return null;
    if (/[<>"']/.test(title) || /[<>"']/.test(slug) || /[<>"']/.test(discipline)) {
        return null;
    }
    return { title, discipline, slug };
}

/**
 * @param {{ title: string, discipline: string, slug: string }} candidate
 * @returns {string}
 */
function candidateKey(candidate) {
    return `${candidate.discipline}:${candidate.slug}:${candidate.title}`;
}

/**
 * @param {HTMLElement} grid
 * @param {{ title: string, discipline: string, slug: string }} candidate
 * @param {HTMLElement} wrap
 * @param {(c: { title: string, discipline: string, slug: string }) => void} onSelect
 */
function appendChipButton(grid, candidate, wrap, onSelect) {
    const { title, discipline, slug } = candidate;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "disambiguation-chip";
    btn.dataset.discipline = discipline;
    btn.dataset.slug = slug;
    btn.dataset.candidateKey = candidateKey(candidate);

    const titleEl = document.createElement("span");
    titleEl.className = "disambiguation-chip__title";
    titleEl.textContent = title;

    const metaEl = document.createElement("span");
    metaEl.className = "disambiguation-chip__meta";
    metaEl.textContent =
        discipline && slug ? `${discipline} · ${slug}` : discipline || slug;

    btn.appendChild(titleEl);
    if (metaEl.textContent) btn.appendChild(metaEl);

    btn.addEventListener("click", () => {
        if (wrap.classList.contains("disambiguation-chips--frozen")) return;
        wrap.classList.add("disambiguation-chips--frozen");
        onSelect?.({ title, discipline, slug });
    });

    grid.appendChild(btn);
}

const LEAD_DEFAULT =
    "Qual destas aulas corresponde melhor à sua pergunta?";
const LEAD_RESCUED =
    "Ligação interrompida — escolha abaixo inicia uma nova pesquisa (não depende da resposta anterior).";

/**
 * Actualiza chips sem remontar os já visíveis (evita flicker e permite stream incremental).
 * @param {HTMLElement} container
 * @param {Array<{ title?: string, discipline?: string, slug?: string }>} candidates
 * @param {{ onSelect: (candidate: { title?: string, discipline?: string, slug?: string }) => void, rescued?: boolean }} handlers
 * @returns {HTMLElement | null}
 */
export function syncDisambiguationChips(container, candidates, { onSelect, rescued = false }) {
    const normalized = [];
    for (const raw of candidates) {
        const c = normalizeCandidate(raw);
        if (c) normalized.push(c);
    }
    if (!normalized.length) return null;

    let wrap = container.querySelector(".disambiguation-chips");
    if (!wrap) {
        wrap = document.createElement("div");
        wrap.className = "disambiguation-chips";
        const lead = document.createElement("p");
        lead.className = "disambiguation-chips__lead";
        lead.textContent = rescued ? LEAD_RESCUED : LEAD_DEFAULT;
        wrap.appendChild(lead);
        const grid = document.createElement("div");
        grid.className = "disambiguation-chips__grid";
        wrap.appendChild(grid);
        container.appendChild(wrap);
    }

    if (rescued) {
        wrap.classList.add("disambiguation-chips--rescued");
        wrap.dataset.rescued = "true";
        const lead = wrap.querySelector(".disambiguation-chips__lead");
        if (lead) lead.textContent = LEAD_RESCUED;
    }

    const grid = wrap.querySelector(".disambiguation-chips__grid");
    if (!grid) return wrap;

    const existing = new Set(
        [...grid.querySelectorAll("button.disambiguation-chip")].map((b) =>
            String(b.dataset.candidateKey || ""),
        ),
    );

    for (const c of normalized) {
        const key = candidateKey(c);
        if (existing.has(key)) continue;
        appendChipButton(grid, c, wrap, onSelect);
    }

    return wrap;
}

/**
 * @param {HTMLElement} container
 * @param {Record<string, unknown>} payload
 * @param {{ onSelect: (candidate: { title?: string, discipline?: string, slug?: string }) => void }} handlers
 * @returns {HTMLElement | null}
 */
export function mountDisambiguationChips(container, payload, { onSelect }) {
    const candidates = payload?.suggested_candidates;
    if (!Array.isArray(candidates) || candidates.length === 0) return null;
    container.querySelector(".disambiguation-chips")?.remove();
    return syncDisambiguationChips(container, candidates, { onSelect });
}

/**
 * @param {HTMLElement} container
 */
export function freezeDisambiguationChips(container) {
    const el = container.querySelector(".disambiguation-chips");
    if (el) el.classList.add("disambiguation-chips--frozen");
}

/**
 * @param {HTMLElement} container
 */
export function invalidateDisambiguationChips(container) {
    const el = container.querySelector(".disambiguation-chips");
    if (!el) return;
    el.classList.add("disambiguation-chips--frozen", "disambiguation-chips--invalidated");
    el.querySelectorAll("button.disambiguation-chip").forEach((btn) => {
        btn.disabled = true;
        btn.setAttribute("aria-disabled", "true");
    });
    const lead = el.querySelector(".disambiguation-chips__lead");
    if (lead) {
        lead.textContent =
            "Estas sugestões foram invalidadas: a resposta não passou na verificação de alinhamento.";
    }
}
