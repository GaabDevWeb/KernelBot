/* =============================================================
   Kernel entrance for the chat landing (empty-state).
   - Full-screen low-poly globe assembles, spins, then glides to
     the LEFT while the title appears on the RIGHT (desktop).
     On mobile the globe settles at the TOP and the title below.
   - The status badge and input slide in at the end.
   - When the chat starts (empty-state hidden), the background
     globe is dismissed — it reappears as a small spinner in the
     "Thinking" indicator while a response loads (see ui.js).
   ============================================================= */

import { createGlobe } from "./globe.js";

(() => {
  "use strict";

  const emptyState = document.getElementById("empty-state");
  const canvas = document.getElementById("globe");

  // Chrome (badge + input) starts hidden via CSS; the entrance reveals it.
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

  // The full-screen background globe. GSAP drives its faces/state.
  const globe = createGlobe(canvas, { sizeTo: "window" });
  const { state, faces } = globe;

  /* ---------- responsive targets (original layout) ---------- */
  const targets = { cx: 0.27, cy: 0.5, scale: 0.92 };

  function computeTargets() {
    if (window.innerWidth <= 820) {
      // Mobile: globe up top, title stacks beneath it.
      targets.cx = 0.5;
      targets.cy = 0.3;
      targets.scale = 0.74;
    } else {
      // Desktop: big globe anchored bottom-left, bleeding off the left and
      // bottom edges (~70% visible). The title sits to the right.
      targets.cx = 0.2;
      targets.cy = 0.78;
      targets.scale = window.innerWidth < 1200 ? 1.45 : 1.8;
    }
  }
  computeTargets();
  window.addEventListener("resize", computeTargets);

  /* ---------- title typing (with a coloured "Kernel") ---------- */
  function typeTitle() {
    const el = document.querySelector(".entrance-title-text");
    const full = "Opa, sou o Kernel! O que precisa hoje?";
    const kStart = full.indexOf("Kernel");
    const kEnd = kStart + "Kernel".length;
    const obj = { n: 0 };
    el.textContent = "";
    return gsap.to(obj, {
      n: full.length,
      duration: 1.8,
      ease: "none",
      onUpdate() {
        const len = Math.round(obj.n);
        const before = full.slice(0, Math.min(len, kStart));
        const kernel = full.slice(kStart, Math.min(len, kEnd));
        const after = len > kEnd ? full.slice(kEnd, len) : "";
        el.innerHTML =
          before +
          (kernel ? `<span class="entrance-kernel">${kernel}</span>` : "") +
          after;
      },
    });
  }

  /* ---------- cycling command suggestions (click to prefill) ---------- */
  function cycleSuggestions() {
    const el = document.querySelector(".entrance-suggestion-text");
    const pill = document.querySelector(".entrance-suggestion");
    const input = document.getElementById("message-input");
    const items = [
      "/python Como listas funcionam?",
      "/sql Como usar GROUP BY?",
      "/carreira Como montar um portfólio?",
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

  /* ---------- master timeline ---------- */
  let idleSpin = null;

  function buildTimeline() {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

    // Plates fly in (staggered) + a gentle drift.
    tl.to(faces, {
      p: 1,
      duration: 1.5,
      ease: "back.out(1.5)",
      stagger: { each: 0.012, from: "random" },
    }, 0.2);
    tl.to(state, { rotY: "+=0.9", duration: 2.2, ease: "sine.inOut" }, 0.2);

    // Full 360° spin.
    tl.to(state, { rotY: "+=" + Math.PI * 2, duration: 2.4, ease: "power2.inOut" }, ">-0.3");

    // Glide to the final position (left on desktop, top on mobile).
    tl.to(state, {
      cx: () => targets.cx,
      cy: () => targets.cy,
      scale: () => targets.scale,
      duration: 1.4,
      ease: "power3.inOut",
    }, "-=0.25");

    // Endless slow idle spin once settled.
    tl.add(() => {
      idleSpin = gsap.to(state, { rotY: "+=" + Math.PI * 2, duration: 26, ease: "none", repeat: -1 });
    });

    // Title reveals + types in (on the right / bottom).
    tl.to(".entrance-content", { autoAlpha: 1, y: 0, duration: 0.7 }, "-=0.5");
    tl.add(typeTitle(), "<0.15");

    // Chat chrome appears: status badge, then the input slides up.
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

    // Suggestion pill fades in and cycles (added last — it repeats forever).
    tl.to(".entrance-suggestion-wrap", { autoAlpha: 1, duration: 0.5 }, "-=0.2");
    tl.add(cycleSuggestions(), "<0.1");

    if (reduce) tl.progress(1);
    return tl;
  }

  /* ---------- dismiss the background globe when the chat starts ---------- */
  const badge = document.getElementById("status-badge");
  const inputArea = document.querySelector(".input-area");

  let dismissed = false;
  let master = null;

  function dismissGlobe() {
    if (dismissed) return;
    dismissed = true;
    // Stop the entrance animation but make sure the chrome ends up visible.
    if (master) master.kill();
    if (idleSpin) idleSpin.kill();
    gsap.set([badge, inputArea].filter(Boolean), { autoAlpha: 1, y: 0 });
    gsap.to(canvas, { autoAlpha: 0, duration: 0.4, onComplete: () => globe.stop() });
  }

  // The chat hides the empty-state (display:none) on the first message.
  const obs = new MutationObserver(() => {
    if (emptyState.style.display === "none") {
      dismissGlobe();
      obs.disconnect();
    }
  });
  obs.observe(emptyState, { attributes: true, attributeFilter: ["style"] });

  /* ---------- boot ---------- */
  gsap.set(".entrance-suggestion-wrap", { autoAlpha: 0 });

  // GSAP owns the chrome's hidden state (drop the CSS fallback class) and gives
  // it a slide-in start offset.
  [badge, inputArea].forEach((el) => el && el.classList.remove("entrance-init-hidden"));
  gsap.set(badge, { autoAlpha: 0, y: -10 });
  gsap.set(inputArea, { autoAlpha: 0, y: 24 });

  master = buildTimeline();
})();
