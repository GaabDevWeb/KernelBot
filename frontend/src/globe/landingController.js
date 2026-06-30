/* =============================================================
   Landing globe — controller canônico (playground = referência).
   ============================================================= */

import { createGlobe } from "../globe.js";
import { attachGlobeInteraction } from "../globe-interaction.js";
import { assignLessonsToFaces } from "../globe-lessons.js";
import { createGlobeTooltip } from "../globe-tooltip.js";
import { syncBodyUiState } from "../utils/uiState.js";

const AUTO_SPIN_DURATION = 26;
const SCALE_FINAL = 0.8;
const HERO_LAT = 5;
const HERO_LON = 10;

/**
 * @param {{
 *   canvas: HTMLCanvasElement,
 *   gsap: typeof import("gsap").gsap | null,
 *   layout?: "landing" | "sandbox",
 *   debug?: boolean,
 * }} opts
 */
export function createLandingGlobeController({
  canvas,
  gsap,
  layout = "landing",
  debug = layout === "sandbox",
}) {
  const tooltip = createGlobeTooltip();

  /** @type {ReturnType<typeof createGlobe> | null} */
  let globe = null;
  /** @type {ReturnType<typeof attachGlobeInteraction> | null} */
  let interaction = null;
  /** @type {import("gsap").core.Tween | null} */
  let idleSpin = null;
  /** @type {import("gsap").core.Timeline | null} */
  let entranceTl = null;
  /** @type {(() => void) | null} */
  let unbindHover = null;
  let dismissed = false;

  const targets = { cx: 0.5, cy: 0.5, scale: 1 };

  function autoSpinOmega() {
    return (Math.PI * 2) / AUTO_SPIN_DURATION;
  }

  function computeTargets() {
    if (window.innerWidth <= 820) {
      targets.cx = 0.5;
      targets.cy = 0.3;
      targets.scale = 0.58 * SCALE_FINAL;
    } else if (window.innerWidth < 1200) {
      targets.cx = 0.38;
      targets.cy = 0.5;
      targets.scale = 1.05 * SCALE_FINAL;
    } else {
      targets.cx = 0.4;
      targets.cy = 0.5;
      targets.scale = 1.28 * SCALE_FINAL;
    }
  }

  function setCanvasInteractive(on) {
    canvas.classList.toggle("is-interactive", on);
    canvas.classList.toggle("is-dismissed", !on);
  }

  function killIdleSpin() {
    idleSpin?.kill();
    idleSpin = null;
  }

  function startIdleSpin() {
    if (!gsap || !globe || dismissed) return;
    killIdleSpin();
    idleSpin = gsap.to(globe.state, {
      rotY: "+=" + Math.PI * 2,
      duration: AUTO_SPIN_DURATION,
      ease: "none",
      repeat: -1,
    });
  }

  function killEntrance() {
    entranceTl?.kill();
    entranceTl = null;
    killIdleSpin();
  }

  function syncTooltip(face, anchor) {
    if (
      face?.lesson &&
      anchor &&
      interaction?.getMode?.() === "auto" &&
      interaction?.isReady?.() &&
      !dismissed
    ) {
      tooltip.show(face.lesson, anchor.clientX, anchor.clientY);
    } else {
      tooltip.hide();
    }
  }

  function wireHover() {
    unbindHover?.();
    unbindHover = globe.onHoverChange((face, anchor) => {
      syncTooltip(face, anchor);
    });
  }

  function wireInteraction() {
    interaction?.destroy();
    interaction = attachGlobeInteraction(canvas, globe, {
      stopAutoSpin: killIdleSpin,
      startAutoSpin: startIdleSpin,
      getAutoSpinOmega: autoSpinOmega,
    });
    interaction.setEnabled(false);

    if (debug) {
      window.__globeDebug = {
        get state() {
          return globe?.state;
        },
        getMode: () => interaction?.getMode?.() ?? "none",
        isReady: () => interaction?.isReady?.() ?? false,
        hitTest: (x, y) => globe?.hitTest(x, y),
        metrics: () => globe?.globeMetrics?.(),
        getHoveredFace: () => globe?.getHoveredFace?.(),
        pickAt: (clientX, clientY) => {
          globe?.setPointer?.(clientX, clientY);
          return globe?.getHoveredFace?.();
        },
        lessonsAssigned: () => globe?.faces?.every((f) => f.lesson) ?? false,
        tooltipVisible: () =>
          !tooltip.el.hidden && tooltip.el.classList.contains("is-visible"),
        tooltipBox: () => tooltip.el.getBoundingClientRect(),
      };
    }
  }

  function mountHero() {
    killEntrance();
    tooltip.hide();
    unbindHover?.();
    if (globe) globe.stop();

    globe = createGlobe(canvas, {
      sizeTo: "window",
      variant: "hero",
      formed: false,
      spin: false,
      particles: true,
    });
    assignLessonsToFaces(globe.faces, HERO_LAT, HERO_LON);
    wireHover();
    wireInteraction();
  }

  function applyRestingState() {
    if (!globe) return;
    computeTargets();
    const { state, faces } = globe;
    for (const f of faces) f.p = 1;
    state.cx = targets.cx;
    state.cy = targets.cy;
    state.scale = targets.scale;
    state.tilt = -0.42;
  }

  /**
   * Timeline GSAP da formação do globo (entrance cinematográfica).
   * @returns {import("gsap").core.Timeline | null}
   */
  function playEntrance() {
    if (!gsap || !globe) return null;

    dismissed = false;
    tooltip.hide();
    globe.setPointer(-1, -1);
    interaction?.setEnabled(false);
    killEntrance();
    computeTargets();
    setCanvasInteractive(true);
    gsap.set(canvas, { autoAlpha: 1 });

    const { state, faces } = globe;
    state.rotY = -0.6;
    state.tilt = -0.42;
    state.cx = 0.5;
    state.cy = 0.5;
    state.scale = 0.85;
    for (const f of faces) f.p = 0;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    entranceTl = gsap.timeline({ defaults: { ease: "power3.out" } });

    entranceTl.to(
      faces,
      {
        p: 1,
        duration: 1.1,
        ease: "back.out(1.5)",
        stagger: { each: 0.01, from: "random" },
      },
      0.15,
    );
    entranceTl.to(state, { rotY: "+=0.9", duration: 1.4, ease: "sine.inOut" }, 0.15);
    entranceTl.to(
      state,
      { rotY: "+=" + Math.PI * 2, duration: 1.6, ease: "power2.inOut" },
      ">-0.2",
    );
    entranceTl.to(
      state,
      {
        cx: () => targets.cx,
        cy: () => targets.cy,
        scale: () => targets.scale,
        duration: 1.0,
        ease: "power3.inOut",
      },
      "-=0.2",
    );
    entranceTl.add(() => {
      startIdleSpin();
      interaction?.setEnabled(true);
      syncBodyUiState();
    });

    if (reduce) {
      entranceTl.progress(1);
      applyRestingState();
      startIdleSpin();
      interaction?.setEnabled(true);
      syncBodyUiState();
    }

    return entranceTl;
  }

  function mountResting() {
    if (!globe) mountHero();
    dismissed = false;
    killEntrance();
    applyRestingState();
    setCanvasInteractive(true);
    globe?.setSpinPaused(false);
    if (gsap) {
      gsap.set(canvas, { autoAlpha: 1 });
    } else {
      canvas.style.opacity = "1";
    }
    startIdleSpin();
    interaction?.setEnabled(true);
    syncBodyUiState();
  }

  function dismiss(fadeMs = 0.4) {
    if (dismissed) return;
    dismissed = true;
    killEntrance();
    tooltip.hide();
    globe?.setPointer(-1, -1);
    interaction?.setEnabled(false);
    setCanvasInteractive(false);

    if (gsap) {
      gsap.to(canvas, {
        autoAlpha: 0,
        duration: fadeMs,
        onComplete: () => globe?.setSpinPaused?.(true),
      });
    } else {
      canvas.style.opacity = "0";
      globe?.setSpinPaused?.(true);
    }
  }

  function restore() {
    dismissed = false;
    if (!globe) {
      mountHero();
    }
    applyRestingState();
    globe?.setSpinPaused(false);
    setCanvasInteractive(true);

    if (gsap) {
      gsap.to(canvas, { autoAlpha: 1, duration: 0.35 });
    } else {
      canvas.style.opacity = "1";
    }

    startIdleSpin();
    interaction?.setEnabled(true);
    syncBodyUiState();
  }

  function onResize() {
    computeTargets();
    if (globe && !dismissed) {
      globe.state.cx = targets.cx;
      globe.state.cy = targets.cy;
      globe.state.scale = targets.scale;
    }
    globe?.resize();
    interaction?.syncIdleRestingCenter?.();
  }

  mountHero();
  setCanvasInteractive(false);
  if (gsap) gsap.set(canvas, { autoAlpha: 0 });

  return {
    playEntrance,
    mountResting,
    dismiss,
    restore,
    onResize,
    replayEntrance: playEntrance,
    getGlobe: () => globe,
    getInteraction: () => interaction,
  };
}
