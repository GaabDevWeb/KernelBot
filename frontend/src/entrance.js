/* =============================================================
   Kernel entrance for the chat landing (empty-state).
   ============================================================= */

import { createGlobe } from "./globe.js";

(() => {
  "use strict";

  const INTRO_SEEN_KEY = "kernel_intro_seen";
  const emptyState = document.getElementById("empty-state");
  const canvas = document.getElementById("globe");

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

  if (hasSeenIntro() || typeof window.gsap === "undefined") {
    revealChromeInstant();
    revealHeroCopy();
    const sub = document.querySelector(".entrance-subtitle");
    if (sub) sub.style.opacity = "1";
    canvas.style.opacity = "0";
    return;
  }

  const gsap = window.gsap;
  const globe = createGlobe(canvas, { sizeTo: "window" });
  const { state, faces } = globe;

  const targets = { cx: 0.27, cy: 0.5, scale: 0.92 };

  function computeTargets() {
    if (window.innerWidth <= 820) {
      targets.cx = 0.5;
      targets.cy = 0.3;
      targets.scale = 0.74;
    } else {
      targets.cx = 0.2;
      targets.cy = 0.78;
      targets.scale = window.innerWidth < 1200 ? 1.45 : 1.8;
    }
  }
  computeTargets();
  window.addEventListener("resize", computeTargets);

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

  let idleSpin = null;

  function buildTimeline() {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const tl = gsap.timeline({
      defaults: { ease: "power3.out" },
      onComplete: markIntroSeen,
    });

    tl.to(faces, {
      p: 1,
      duration: 1.1,
      ease: "back.out(1.5)",
      stagger: { each: 0.01, from: "random" },
    }, 0.15);
    tl.to(state, { rotY: "+=0.9", duration: 1.4, ease: "sine.inOut" }, 0.15);
    tl.to(state, { rotY: "+=" + Math.PI * 2, duration: 1.6, ease: "power2.inOut" }, ">-0.2");
    tl.to(state, {
      cx: () => targets.cx,
      cy: () => targets.cy,
      scale: () => targets.scale,
      duration: 1.0,
      ease: "power3.inOut",
    }, "-=0.2");

    tl.add(() => {
      idleSpin = gsap.to(state, { rotY: "+=" + Math.PI * 2, duration: 26, ease: "none", repeat: -1 });
    });

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

  const badge = document.getElementById("status-badge");
  const newChatBtn = document.getElementById("new-chat-button");
  const inputArea = document.querySelector(".input-area");

  let dismissed = false;
  let master = null;

  function dismissGlobe() {
    if (dismissed) return;
    dismissed = true;
    if (master) master.kill();
    if (idleSpin) idleSpin.kill();
    gsap.set([badge, newChatBtn, inputArea].filter(Boolean), { autoAlpha: 1, y: 0 });
    gsap.to(canvas, { autoAlpha: 0, duration: 0.35, onComplete: () => globe.stop() });
  }

  const obs = new MutationObserver(() => {
    if (emptyState.style.display === "none") {
      dismissGlobe();
      obs.disconnect();
    }
  });
  obs.observe(emptyState, { attributes: true, attributeFilter: ["style"] });

  gsap.set(".entrance-suggestion-wrap", { autoAlpha: 0 });
  gsap.set(".entrance-discipline-pills", { autoAlpha: 0, y: 8 });
  gsap.set(".entrance-subtitle", { autoAlpha: 0, y: 6 });

  [badge, newChatBtn, inputArea].forEach((el) => el && el.classList.remove("entrance-init-hidden"));
  gsap.set(badge, { autoAlpha: 0, y: 0 });
  gsap.set(newChatBtn, { autoAlpha: 0, y: 0 });
  gsap.set(inputArea, { autoAlpha: 0, y: 20 });

  master = buildTimeline();
})();
