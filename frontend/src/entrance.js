/* =============================================================
   Kernel entrance for the chat landing (empty-state).
   ============================================================= */

import { createGlobe } from "./globe.js";

(() => {
  "use strict";

  const emptyState = document.getElementById("empty-state");
  const canvas = document.getElementById("globe");

  function revealChromeInstant() {
    document
      .querySelectorAll(".entrance-init-hidden")
      .forEach((el) => el.classList.remove("entrance-init-hidden"));
  }

  if (!emptyState || !canvas || typeof window.gsap === "undefined") {
    revealChromeInstant();
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

  function revealHeroCopy() {
    const titleEl = document.querySelector(".entrance-title-text");
    if (titleEl) {
      titleEl.innerHTML =
        'Estude por <span class="entrance-kernel">disciplinas</span>';
    }
    let sub = document.querySelector(".entrance-subtitle");
    if (!sub) {
      sub = document.createElement("p");
      sub.className = "entrance-subtitle";
      const headline = document.querySelector(".entrance-headline");
      headline?.insertAdjacentElement("afterend", sub);
    }
    sub.textContent =
      "Consulte materiais do curso e receba respostas fundamentadas nas aulas indexadas.";
  }

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
      tl.to({}, { duration: 1.6 });
      tl.to(obj, { n: 0, duration: text.length * 0.025, ease: "none", onUpdate: render });
      tl.call(() => (current = ""));
      tl.to({}, { duration: 0.35 });
    });
    return tl;
  }

  let idleSpin = null;

  function buildTimeline() {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

    tl.to(faces, {
      p: 1,
      duration: 1.5,
      ease: "back.out(1.5)",
      stagger: { each: 0.012, from: "random" },
    }, 0.2);
    tl.to(state, { rotY: "+=0.9", duration: 2.2, ease: "sine.inOut" }, 0.2);
    tl.to(state, { rotY: "+=" + Math.PI * 2, duration: 2.4, ease: "power2.inOut" }, ">-0.3");
    tl.to(state, {
      cx: () => targets.cx,
      cy: () => targets.cy,
      scale: () => targets.scale,
      duration: 1.4,
      ease: "power3.inOut",
    }, "-=0.25");

    tl.add(() => {
      idleSpin = gsap.to(state, { rotY: "+=" + Math.PI * 2, duration: 26, ease: "none", repeat: -1 });
    });

    tl.to(".entrance-content", { autoAlpha: 1, y: 0, duration: 0.7 }, "-=0.5");
    tl.add(revealHeroCopy, "<0.1");
    tl.to(".entrance-subtitle", { autoAlpha: 1, y: 0, duration: 0.5 }, "-=0.35");
    tl.to(".entrance-discipline-pills", { autoAlpha: 1, y: 0, duration: 0.55, stagger: 0.04 }, "-=0.2");

    tl.to("#status-badge", { autoAlpha: 1, y: 0, duration: 0.6 }, "-=0.4");
    tl.to(".input-area", {
      autoAlpha: 1,
      y: 0,
      duration: 0.8,
      ease: "power3.out",
      onComplete() {
        const input = document.getElementById("message-input");
        if (input) input.focus();
      },
    }, "-=0.3");

    tl.to(".entrance-suggestion-wrap", { autoAlpha: 1, duration: 0.5 }, "-=0.2");
    tl.add(cycleSuggestions(), "<0.1");

    if (reduce) tl.progress(1);
    return tl;
  }

  const badge = document.getElementById("status-badge");
  const inputArea = document.querySelector(".input-area");

  let dismissed = false;
  let master = null;

  function dismissGlobe() {
    if (dismissed) return;
    dismissed = true;
    if (master) master.kill();
    if (idleSpin) idleSpin.kill();
    gsap.set([badge, inputArea].filter(Boolean), { autoAlpha: 1, y: 0 });
    gsap.to(canvas, { autoAlpha: 0, duration: 0.4, onComplete: () => globe.stop() });
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

  [badge, inputArea].forEach((el) => el && el.classList.remove("entrance-init-hidden"));
  gsap.set(badge, { autoAlpha: 0, y: -10 });
  gsap.set(inputArea, { autoAlpha: 0, y: 24 });

  master = buildTimeline();
})();
