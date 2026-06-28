/* =============================================================
   Kernel entrance for the chat landing (empty-state).
   ============================================================= */

import { createLandingGlobeController } from "./globe/landingController.js";

(() => {
  "use strict";

  const INTRO_SEEN_KEY = "kernel_intro_seen";

  const emptyState = document.getElementById("empty-state");
  const canvas = document.getElementById("globe");

  /** @type {ReturnType<typeof createLandingGlobeController> | null} */
  let controller = null;
  /** @type {import("gsap").core.Timeline | null} */
  let master = null;

  function revealChromeInstant() {
    document
      .querySelectorAll(".entrance-init-hidden")
      .forEach((el) => el.classList.remove("entrance-init-hidden"));
  }

  function markIntroSeen() {
    try {
      sessionStorage.setItem(INTRO_SEEN_KEY, "1");
    } catch {
      /* quota / private mode */
    }
  }

  function hasSeenIntro() {
    try {
      return sessionStorage.getItem(INTRO_SEEN_KEY) === "1";
    } catch {
      return false;
    }
  }

  function revealHeroCopy() {
    const titleEl = document.querySelector(".entrance-title-text");
    if (titleEl) {
      titleEl.innerHTML =
        'Estude por <span class="entrance-kernel">disciplinas</span>';
    }
    const sub = document.querySelector(".entrance-subtitle");
    if (sub) {
      sub.textContent =
        "Consulte materiais do curso e receba respostas fundamentadas nas aulas indexadas.";
    }
  }

  if (!emptyState || !canvas) {
    revealChromeInstant();
    return;
  }

  const gsap = typeof window.gsap !== "undefined" ? window.gsap : null;

  controller = createLandingGlobeController({
    canvas,
    gsap,
    layout: "landing",
  });

  window.__kernelGlobe = controller;

  window.addEventListener("kernel:show-landing", () => {
    controller?.restore();
  });

  window.addEventListener("resize", () => {
    controller?.onResize();
  });

  if (hasSeenIntro() || !gsap) {
    revealChromeInstant();
    revealHeroCopy();
    const sub = document.querySelector(".entrance-subtitle");
    if (sub) sub.style.opacity = "1";
    controller.mountResting();
  } else {
    const badge = document.getElementById("status-badge");
    const newChatBtn = document.getElementById("new-chat-button");
    const inputArea = document.querySelector(".input-area");

    function cycleSuggestions() {
      const el = document.querySelector(".entrance-suggestion-text");
      const pill = document.querySelector(".entrance-suggestion");
      const input = document.getElementById("message-input");
      const items = [
        "/python Como listas funcionam?",
        "/visualizacao-sql Como usar GROUP BY?",
        "/planejamento-curso-carreira Como montar um portfólio?",
        "/fluencia-ia Qual a diferença entre ML e DL?",
        "/python-processamento-dados Como funciona try except?",
        "/sql-modelagem-relacional O que é normalização 3FN?",
        "/projeto-bloco Como estruturar o mini-projeto?",
        "/doc Como o sistema funciona?",
      ];

      let current = "";
      if (pill && input) {
        pill.addEventListener("click", () => {
          if (!current) return;
          input.value = current;
          input.dispatchEvent(new Event("input"));
          input.focus();
          input.selectionStart = input.selectionEnd = input.value.length;
        });
      }

      const tl = gsap.timeline({ repeat: -1 });
      items.forEach((text) => {
        const obj = { n: 0 };
        const render = () => (el.textContent = text.slice(0, Math.round(obj.n)));
        tl.call(() => (current = text));
        tl.to(obj, { n: text.length, duration: text.length * 0.045, ease: "none", onUpdate: render });
        tl.to({}, { duration: 1.2 });
        tl.to(obj, { n: 0, duration: text.length * 0.025, ease: "none", onUpdate: render });
        tl.call(() => (current = ""));
        tl.to({}, { duration: 0.25 });
      });
      return tl;
    }

    function buildTimeline() {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      const entranceGlobe = controller.playEntrance();
      const tl = gsap.timeline({
        defaults: { ease: "power3.out" },
        onComplete: markIntroSeen,
      });

      if (entranceGlobe) tl.add(entranceGlobe, 0);

      tl.to(".entrance-content", { autoAlpha: 1, y: 0, duration: 0.55 }, "-=0.35");
      tl.call(revealHeroCopy, undefined, "<0.05");
      tl.to(".entrance-subtitle", { autoAlpha: 1, y: 0, duration: 0.4 }, "-=0.25");
      tl.to(".entrance-discipline-pills", { autoAlpha: 1, y: 0, duration: 0.45, stagger: 0.03 }, "-=0.15");

      tl.to("#status-badge", { autoAlpha: 1, y: 0, duration: 0.45 }, "-=0.3");
      tl.to("#new-chat-button", { autoAlpha: 1, y: 0, duration: 0.45 }, "<");
      tl.to(".input-area", {
        autoAlpha: 1,
        y: 0,
        duration: 0.6,
        ease: "power3.out",
        onComplete() {
          const input = document.getElementById("message-input");
          if (input) input.focus();
        },
      }, "-=0.25");

      tl.to(".entrance-suggestion-wrap", { autoAlpha: 1, duration: 0.4 }, "-=0.15");
      tl.add(cycleSuggestions(), "<0.05");

      if (reduce) tl.progress(1);
      return tl;
    }

    gsap.set(".entrance-suggestion-wrap", { autoAlpha: 0 });
    gsap.set(".entrance-discipline-pills", { autoAlpha: 0, y: 8 });
    gsap.set(".entrance-subtitle", { autoAlpha: 0, y: 6 });

    [badge, newChatBtn, inputArea].forEach((el) => el && el.classList.remove("entrance-init-hidden"));
    gsap.set(badge, { autoAlpha: 0, y: 0 });
    gsap.set(newChatBtn, { autoAlpha: 0, y: 0 });
    gsap.set(inputArea, { autoAlpha: 0, y: 20 });

    master = buildTimeline();
  }

  const obs = new MutationObserver(() => {
    if (emptyState.style.display === "none") {
      if (master) master.kill();
      controller?.dismiss(hasSeenIntro() ? 0.35 : 0.4);
    }
  });
  obs.observe(emptyState, { attributes: true, attributeFilter: ["style"] });
})();
