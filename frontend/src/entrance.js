/* =============================================================
   Kernel entrance for the chat landing (empty-state).
   ============================================================= */

import { createLandingGlobeController } from "./globe/landingController.js";
import { revealComposerChrome } from "./utils/uiState.js";

(() => {
  "use strict";

  const INTRO_SEEN_KEY = "kernel_intro_seen";

  const emptyState = document.getElementById("empty-state");
  const canvas = document.getElementById("globe");

  /** @type {ReturnType<typeof createLandingGlobeController> | null} */
  let controller = null;
  /** @type {import("gsap").core.Timeline | null} */
  let master = null;
  /** @type {import("gsap").core.Timeline | null} */
  let suggestionTl = null;
  let suggestionClickBound = false;

  function revealChromeInstant() {
    revealComposerChrome();
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

  function resetLandingVisuals() {
    revealHeroCopy();
    if (gsap) {
      gsap.set(".entrance-content", { autoAlpha: 1, y: 0, clearProps: "transform" });
      gsap.set(".entrance-subtitle", { autoAlpha: 1, y: 0, clearProps: "transform" });
      gsap.set(".entrance-discipline-pills", { autoAlpha: 1, y: 0, clearProps: "transform" });
      gsap.set(".entrance-suggestion-wrap", { autoAlpha: 1 });
      return;
    }

    const content = document.querySelector(".entrance-content");
    const sub = document.querySelector(".entrance-subtitle");
    const pills = document.querySelector(".entrance-discipline-pills");
    const wrap = document.querySelector(".entrance-suggestion-wrap");
    if (content) {
      content.style.opacity = "1";
      content.style.transform = "none";
    }
    if (sub) sub.style.opacity = "1";
    if (pills) pills.style.opacity = "1";
    if (wrap) wrap.style.opacity = "1";
  }

  function stopSuggestions() {
    suggestionTl?.kill();
    suggestionTl = null;
  }

  function cycleSuggestions() {
    if (!gsap) return null;

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
    if (pill && input && !suggestionClickBound) {
      suggestionClickBound = true;
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
      const render = () => {
        if (el) el.textContent = text.slice(0, Math.round(obj.n));
      };
      tl.call(() => {
        current = text;
      });
      tl.to(obj, {
        n: text.length,
        duration: text.length * 0.045,
        ease: "none",
        onUpdate: render,
      });
      tl.to({}, { duration: 1.2 });
      tl.to(obj, {
        n: 0,
        duration: text.length * 0.025,
        ease: "none",
        onUpdate: render,
      });
      tl.call(() => {
        current = "";
      });
      tl.to({}, { duration: 0.25 });
    });
    return tl;
  }

  function startSuggestions() {
    stopSuggestions();
    suggestionTl = cycleSuggestions();
  }

  function activateLanding() {
    resetLandingVisuals();
    revealChromeInstant();
    startSuggestions();
    controller?.restore();
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
    activateLanding();
  });

  window.addEventListener("kernel:chat-active", () => {
    stopSuggestions();
    controller?.dismiss(0);
  });

  window.addEventListener("resize", () => {
    controller?.onResize();
  });

  if (hasSeenIntro() || !gsap) {
    resetLandingVisuals();
    revealChromeInstant();
    startSuggestions();
    controller?.mountResting();
  } else {
    const inputArea = document.querySelector(".input-area");

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

      tl.to(
        ".input-area",
        {
          autoAlpha: 1,
          y: 0,
          duration: 0.6,
          ease: "power3.out",
          onComplete() {
            const input = document.getElementById("message-input");
            if (input) input.focus();
          },
        },
        "-=0.25",
      );

      tl.to(".entrance-suggestion-wrap", { autoAlpha: 1, duration: 0.4 }, "-=0.15");
      tl.add(() => {
        startSuggestions();
      }, "<0.05");

      if (reduce) tl.progress(1);
      return tl;
    }

    gsap.set(".entrance-suggestion-wrap", { autoAlpha: 0 });
    gsap.set(".entrance-discipline-pills", { autoAlpha: 0, y: 8 });
    gsap.set(".entrance-subtitle", { autoAlpha: 0, y: 6 });

    inputArea?.classList.remove("entrance-init-hidden");
    if (inputArea) gsap.set(inputArea, { autoAlpha: 0, y: 20 });

    master = buildTimeline();
  }

  const obs = new MutationObserver(() => {
    if (emptyState.style.display === "none") {
      if (master) {
        master.kill();
        master = null;
      }
      stopSuggestions();
      revealComposerChrome();
      controller?.dismiss(hasSeenIntro() ? 0.35 : 0.4);
    }
  });
  obs.observe(emptyState, { attributes: true, attributeFilter: ["style"] });
})();
