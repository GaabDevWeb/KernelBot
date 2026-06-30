/* =============================================================
   Tooltip premium para placas do globo (playground).
   ============================================================= */

const MARGIN = 14;
const OFFSET_X = 18;
const OFFSET_Y = -20;
const HIDE_MS = 300;
const CONTENT_FADE_MS = 140;

/**
 * @param {HTMLElement} [root]
 */
export function createGlobeTooltip(root = document.body) {
  const el = document.createElement("div");
  el.className = "globe-tooltip";
  el.setAttribute("role", "tooltip");
  el.hidden = true;
  el.innerHTML = `
    <div class="globe-tooltip__body">
      <span class="globe-tooltip__label">Aula</span>
      <p class="globe-tooltip__title"></p>
      <span class="globe-tooltip__label">Disciplina</span>
      <p class="globe-tooltip__discipline"></p>
    </div>
  `;
  root.appendChild(el);

  const titleEl = el.querySelector(".globe-tooltip__title");
  const discEl = el.querySelector(".globe-tooltip__discipline");

  let visible = false;
  let anchorX = 0;
  let anchorY = 0;
  let currentLessonKey = "";
  let contentTimer = 0;
  let hideTimer = 0;

  function lessonKey(lesson) {
    return `${lesson.discipline}::${lesson.title}`;
  }

  function clampPosition(left, top) {
    const w = el.offsetWidth;
    const h = el.offsetHeight;
    const maxLeft = window.innerWidth - w - MARGIN;
    const maxTop = window.innerHeight - h - MARGIN;
    return {
      left: Math.min(Math.max(MARGIN, left), Math.max(MARGIN, maxLeft)),
      top: Math.min(Math.max(MARGIN, top), Math.max(MARGIN, maxTop)),
    };
  }

  function applyPosition() {
    const { left, top } = clampPosition(anchorX + OFFSET_X, anchorY + OFFSET_Y);
    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
  }

  function setLessonContent(lesson) {
    titleEl.textContent = lesson.title;
    discEl.textContent = lesson.discipline;
    currentLessonKey = lessonKey(lesson);
  }

  function updateLessonContent(lesson) {
    const key = lessonKey(lesson);
    if (key === currentLessonKey) return;

    window.clearTimeout(contentTimer);
    el.classList.add("is-content-fading");

    contentTimer = window.setTimeout(() => {
      setLessonContent(lesson);
      el.classList.remove("is-content-fading");
    }, CONTENT_FADE_MS);
  }

  function reveal() {
    el.hidden = false;
    el.classList.remove("is-leaving", "is-visible", "is-content-fading");
    void el.offsetWidth;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.classList.add("is-visible");
      });
    });
  }

  function show(lesson, x, y) {
    window.clearTimeout(hideTimer);
    anchorX = x;
    anchorY = y;

    if (!visible) {
      setLessonContent(lesson);
      reveal();
      visible = true;
      requestAnimationFrame(applyPosition);
      return;
    }

    updateLessonContent(lesson);
    applyPosition();
  }

  function move(x, y) {
    if (!visible) return;
    anchorX = x;
    anchorY = y;
    applyPosition();
  }

  function hide() {
    if (!visible) return;
    visible = false;
    currentLessonKey = "";
    window.clearTimeout(contentTimer);
    el.classList.remove("is-visible", "is-content-fading");
    el.classList.add("is-leaving");
    hideTimer = window.setTimeout(() => {
      if (!visible) {
        el.hidden = true;
        el.classList.remove("is-leaving");
      }
    }, HIDE_MS);
  }

  window.addEventListener("resize", () => {
    if (visible) applyPosition();
  });

  return { show, move, hide, el };
}
