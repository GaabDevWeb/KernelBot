/* =============================================================
   Drag + inertia + handoff for the low-poly globe (playground).
   Preserves external auto-spin (GSAP or internal spin) at rest.
   ============================================================= */

const SENS_X = 0.0052;
const SENS_Y = 0.0031;
const FRICTION = 3.8;
const VELOCITY_STOP = 0.018;
const HANDOFF_MS = 1600;
const INERTIA_MAX_MS = 2400;
const TILT_MIN = -0.88;
const TILT_MAX = 0.18;

/**
 * @param {HTMLCanvasElement} canvas
 * @param {ReturnType<import("./globe.js").createGlobe>} globe
 * @param {{
 *   stopAutoSpin: () => void,
 *   startAutoSpin: () => void,
 *   getAutoSpinOmega?: () => number,
 * }} options
 */
export function attachGlobeInteraction(canvas, globe, options) {
  const { state, hitTest, getDefaultTilt } = globe;

  let enabled = false;
  let ready = false;
  let mode = "auto"; // auto | drag | inertia | handoff
  let pointerId = null;
  let lastX = 0;
  let lastY = 0;
  let lastT = 0;
  let velRotY = 0;
  let velTilt = 0;
  let motionRaf = 0;
  let handoffStart = 0;
  let handoffFromVel = 0;
  let handoffFromTilt = 0;
  let handoffLastT = 0;
  let inertiaStart = 0;

  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function autoOmega() {
    const internal = globe.getAutoSpinOmega?.() || 0;
    if (internal > 0) return internal;
    return options.getAutoSpinOmega?.() || 0;
  }

  function clampTilt(value) {
    return Math.min(TILT_MAX, Math.max(TILT_MIN, value));
  }

  function setCursor(kind) {
    canvas.classList.remove("is-grabbable", "is-grabbing");
    if (kind === "grab") canvas.classList.add("is-grabbable");
    if (kind === "grabbing") canvas.classList.add("is-grabbing");
  }

  function cancelMotionLoop() {
    if (motionRaf) cancelAnimationFrame(motionRaf);
    motionRaf = 0;
  }

  function stopAutoSpin() {
    options.stopAutoSpin();
    globe.setSpinPaused?.(true);
  }

  function startAutoSpin() {
    globe.setSpinPaused?.(false);
    options.startAutoSpin();
    mode = "auto";
  }

  function finishHandoff(now) {
    cancelMotionLoop();
    startAutoSpin();
    handoffLastT = now;
  }

  function handoffStep(now) {
    if (mode !== "handoff") return;

    const dt = Math.min(0.032, Math.max(0.001, (now - handoffLastT) / 1000));
    handoffLastT = now;
    const t = Math.min(1, (now - handoffStart) / HANDOFF_MS);
    const ease = 1 - Math.pow(1 - t, 3);
    const targetOmega = autoOmega();
    const omega = handoffFromVel + (targetOmega - handoffFromVel) * ease;
    const tiltTarget = getDefaultTilt();

    state.rotY += omega * dt;
    state.tilt = handoffFromTilt + (tiltTarget - handoffFromTilt) * ease;

    if (t >= 1) {
      finishHandoff(now);
      return;
    }

    motionRaf = requestAnimationFrame(handoffStep);
  }

  function beginHandoff() {
    mode = "handoff";
    handoffStart = performance.now();
    handoffLastT = handoffStart;
    handoffFromVel = velRotY;
    handoffFromTilt = state.tilt;
    cancelMotionLoop();
    motionRaf = requestAnimationFrame(handoffStep);
  }

  function inertiaStep(now) {
    if (mode !== "inertia") return;

    const dt = Math.min(0.032, Math.max(0.001, (now - lastT) / 1000));
    lastT = now;

    state.rotY += velRotY * dt;
    state.tilt = clampTilt(state.tilt + velTilt * dt);

    const decay = Math.exp(-FRICTION * dt);
    velRotY *= decay;
    velTilt *= decay;

    const tiltTarget = getDefaultTilt();
    state.tilt += (tiltTarget - state.tilt) * Math.min(1, dt * 2.8);

    if (
      Math.abs(velRotY) < VELOCITY_STOP ||
      now - inertiaStart > INERTIA_MAX_MS
    ) {
      velRotY = 0;
      velTilt = 0;
      beginHandoff();
      return;
    }

    motionRaf = requestAnimationFrame(inertiaStep);
  }

  function updateHoverCursor(clientX, clientY) {
    if (!ready || mode !== "auto" || pointerId !== null) return;
    setCursor(hitTest(clientX, clientY) ? "grab" : null);
  }

  function beginInertia() {
    if (prefersReducedMotion) {
      velRotY = 0;
      velTilt = 0;
      beginHandoff();
      return;
    }

    mode = "inertia";
    lastT = performance.now();
    inertiaStart = lastT;
    cancelMotionLoop();
    motionRaf = requestAnimationFrame(inertiaStep);
  }

  function onPointerDown(e) {
    if (!ready || e.button !== 0) return;
    if (!hitTest(e.clientX, e.clientY)) return;

    e.preventDefault();
    cancelMotionLoop();
    stopAutoSpin();

    pointerId = e.pointerId;
    mode = "drag";
    lastX = e.clientX;
    lastY = e.clientY;
    lastT = performance.now();
    velRotY = 0;
    velTilt = 0;

    canvas.setPointerCapture(e.pointerId);
    setCursor("grabbing");
  }

  function onPointerMove(e) {
    if (mode === "drag" && e.pointerId === pointerId) {
      e.preventDefault();
      const now = performance.now();
      const dt = Math.max(0.001, (now - lastT) / 1000);
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;

      const dRotY = dx * SENS_X;
      const dTilt = dy * SENS_Y;

      state.rotY += dRotY;
      state.tilt = clampTilt(state.tilt + dTilt);

      const instantRotY = dRotY / dt;
      const instantTilt = dTilt / dt;
      velRotY = velRotY * 0.35 + instantRotY * 0.65;
      velTilt = velTilt * 0.35 + instantTilt * 0.65;

      lastX = e.clientX;
      lastY = e.clientY;
      lastT = now;
      return;
    }

    updateHoverCursor(e.clientX, e.clientY);
  }

  function onMouseMove(e) {
    updateHoverCursor(e.clientX, e.clientY);
  }

  function endDrag(e) {
    if (e.pointerId !== pointerId) return;

    if (canvas.hasPointerCapture(e.pointerId)) {
      canvas.releasePointerCapture(e.pointerId);
    }
    pointerId = null;

    if (mode !== "drag") return;

    const speed = Math.hypot(velRotY, velTilt);
    if (speed < VELOCITY_STOP * 0.5) {
      velRotY = 0;
      velTilt = 0;
      beginHandoff();
    } else {
      beginInertia();
    }

    setCursor(hitTest(e.clientX, e.clientY) ? "grab" : null);
  }

  function onPointerUp(e) {
    endDrag(e);
  }

  function onPointerCancel(e) {
    if (e.pointerId !== pointerId) return;
    pointerId = null;
    mode = "auto";
    cancelMotionLoop();
    setCursor(null);
    startAutoSpin();
  }

  function onLostCapture() {
    if (pointerId === null || mode !== "drag") return;
    pointerId = null;
    beginInertia();
    setCursor(null);
  }

  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerup", onPointerUp);
  canvas.addEventListener("pointercancel", onPointerCancel);
  canvas.addEventListener("lostpointercapture", onLostCapture);
  canvas.addEventListener("mousemove", onMouseMove);

  return {
    getMode: () => mode,
    isReady: () => ready,
    setEnabled(value) {
      enabled = Boolean(value);
      ready = enabled;
      if (!enabled) {
        ready = false;
        cancelMotionLoop();
        pointerId = null;
        mode = "auto";
        setCursor(null);
      }
    },
    destroy() {
      cancelMotionLoop();
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", onPointerUp);
      canvas.removeEventListener("pointercancel", onPointerCancel);
      canvas.removeEventListener("lostpointercapture", onLostCapture);
      canvas.removeEventListener("mousemove", onMouseMove);
      setCursor(null);
    },
  };
}
