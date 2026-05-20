/**
 * Alerta operacional: aula no catálogo, ausente do índice BM25 local.
 * @param {HTMLElement} container — bubble da mensagem em streaming
 * @param {Record<string, unknown>} payload — `expected_lesson`, `suggested_candidates`
 * @returns {HTMLElement | null}
 */
export function mountIndexGapAlert(container, payload) {
    const lesson = payload?.expected_lesson;
    if (!lesson || typeof lesson !== "object") return null;

    const title = String(lesson.title || lesson.slug || "Aula").trim();
    const discipline = String(lesson.discipline || "—").trim();
    const slug = String(lesson.slug || "—").trim();

    const alert = document.createElement("div");
    alert.className = "index-gap-alert";

    const heading = document.createElement("p");
    heading.className = "index-gap-alert__title";
    heading.textContent = "Conteúdo ainda não indexado";

    const body = document.createElement("p");
    body.className = "index-gap-alert__body";
    body.textContent =
        "Esta aula consta no catálogo, mas o material ainda não está disponível na busca local.";

    const meta = document.createElement("dl");
    meta.className = "index-gap-alert__meta";

    for (const [label, value] of [
        ["Aula", title],
        ["Disciplina", discipline],
        ["Slug", slug],
    ]) {
        const row = document.createElement("div");
        row.className = "index-gap-alert__row";
        const dt = document.createElement("dt");
        dt.textContent = label;
        const dd = document.createElement("dd");
        dd.textContent = value;
        row.appendChild(dt);
        row.appendChild(dd);
        meta.appendChild(row);
    }

    const hint = document.createElement("p");
    hint.className = "index-gap-alert__hint";
    hint.textContent =
        "Peça ao responsável para atualizar o índice ou envie `/reload` após a indexação.";

    alert.appendChild(heading);
    alert.appendChild(body);
    alert.appendChild(meta);
    alert.appendChild(hint);
    container.appendChild(alert);
    return alert;
}
