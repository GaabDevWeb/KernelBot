/**
 * Chips de desambiguação a partir de `suggested_candidates`.
 * @param {HTMLElement} container — bubble da mensagem em streaming
 * @param {Record<string, unknown>} payload
 * @param {{ onSelect: (candidate: { title?: string, discipline?: string, slug?: string }) => void }} handlers
 * @returns {HTMLElement | null}
 */
export function mountDisambiguationChips(container, payload, { onSelect }) {
    const candidates = payload?.suggested_candidates;
    if (!Array.isArray(candidates) || candidates.length === 0) return null;

    const wrap = document.createElement("div");
    wrap.className = "disambiguation-chips";

    const lead = document.createElement("p");
    lead.className = "disambiguation-chips__lead";
    lead.textContent = "Qual destas aulas corresponde melhor à sua pergunta?";
    wrap.appendChild(lead);

    const grid = document.createElement("div");
    grid.className = "disambiguation-chips__grid";

    for (const raw of candidates) {
        if (!raw || typeof raw !== "object") continue;
        const title = String(raw.title || raw.slug || "Aula").trim();
        const discipline = String(raw.discipline || "").trim();
        const slug = String(raw.slug || "").trim();

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "disambiguation-chip";
        btn.dataset.discipline = discipline;
        btn.dataset.slug = slug;

        const titleEl = document.createElement("span");
        titleEl.className = "disambiguation-chip__title";
        titleEl.textContent = title;

        const metaEl = document.createElement("span");
        metaEl.className = "disambiguation-chip__meta";
        metaEl.textContent = discipline && slug ? `${discipline} · ${slug}` : discipline || slug;

        btn.appendChild(titleEl);
        if (metaEl.textContent) btn.appendChild(metaEl);

        btn.addEventListener("click", () => {
            if (wrap.classList.contains("disambiguation-chips--frozen")) return;
            wrap.classList.add("disambiguation-chips--frozen");
            onSelect?.({ title, discipline, slug });
        });

        grid.appendChild(btn);
    }

    if (!grid.childElementCount) return null;

    wrap.appendChild(grid);
    container.appendChild(wrap);
    return wrap;
}

/**
 * @param {HTMLElement} container
 */
export function freezeDisambiguationChips(container) {
    const el = container.querySelector(".disambiguation-chips");
    if (el) el.classList.add("disambiguation-chips--frozen");
}
