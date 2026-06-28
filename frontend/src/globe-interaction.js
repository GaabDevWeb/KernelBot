/* =============================================================
   Drag + inertia + handoff for the low-poly globe.
   Preserves external auto-spin (GSAP or internal spin) at rest.
   ============================================================= */

const SENS_X = 0.003;
const SENS_Y = 0.00175;
const DRAG_FOLLOW = 7.2;
const FRICTION = 3.8;
const VELOCITY_STOP = 0.016;
const HANDOFF_MS = 1700;
const INERTIA_MAX_MS = 2600;
const TILT_MIN = -0.88;
const TILT_MAX = 0.18;

/**
 * @param {HTMLCanvasElement} canvas
 * @param {ReturnType<import("./globe.js").createGlobe>} globe
 * @param {{
 *   stopAutoSpin: () => void,
 *   startAutoSpin: () => void,
 *   getAutoSpinOmega?: () => number,
 *   onPlateHover?: (face: object | null, anchor: object | null) => void,
 * }} options
 */
export function attachGlobeInteraction(canvas, globe, options) {
  const { state, hitTest, getDefaultTilt } = globe;

  let enabled = false;
  let ready = false;
  let mode = "auto"; // auto | drag | inertia | handoff
  let pointerId = null;
  let pointerX = 0;
  let pointerY = 0;
  let followX = 0;
  let followY = 0;
  let lastT = 0;
  let dragLastT = 0;
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
    canvas.classList.remove("is-grabbable", "is-grabbing", "is-plate-hover");
    if (kind === "grab") canvas.classList.add("is-grabbable");
    if (kind === "grabbing") canvas.classList.add("is-grabbing");
    if (kind === "plate") canvas.classList.add("is-plate-hover");
  }

  function clearPlatePointer() {
    globe.setPointer?.(-1, -1);
    options.onPlateHover?.(null, null);
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
    state.tilt += (tiltTarget - state.tilt) * Math.min(1, dt * 2.4);

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
    if (!ready || pointerId !== null) return;

    globe.setPointer?.(clientX, clientY);

    if (mode === "auto" && globe.getHoveredFace?.()?.lesson) {
      setCursor("plate");
      return;
    }
    if (mode === "auto") {
      setCursor(hitTest(clientX, clientY) ? "grab" : null);
      return;
    }
    setCursor(null);
  }

  function applyDragDelta(dx, dy, dt) {
    if (Math.abs(dx) < 0.002 && Math.abs(dy) < 0.002) return;

    const dRotY = dx * SENS_X;
    const dTilt = dy * SENS_Y;

    state.rotY += dRotY;
    state.tilt = clampTilt(state.tilt + dTilt);

    if (dt > 0) {
      const instantRotY = dRotY / dt;
      const instantTilt = dTilt / dt;
      velRotY = velRotY * 0.55 + instantRotY * 0.45;
      velTilt = velTilt * 0.55 + instantTilt * 0.45;
    }
  }

  function flushDragLag() {
    const dx = pointerX - followX;
    const dy = pointerY - followY;
    if (Math.abs(dx) > 0.4 || Math.abs(dy) > 0.4) {
      applyDragDelta(dx, dy, 0.016);
    }
    followX = pointerX;
    followY = pointerY;
  }

  function dragStep(now) {
    if (mode !== "drag") return;

    const dt = Math.min(0.032, Math.max(0.001, (now - dragLastT) / 1000));
    dragLastT = now;

    const k = 1 - Math.exp(-DRAG_FOLLOW * dt);
    const prevFX = followX;
    const prevFY = followY;

    followX += (pointerX - followX) * k;
    followY += (pointerY - followY) * k;

    applyDragDelta(followX - prevFX, followY - prevFY, dt);

    motionRaf = requestAnimationFrame(dragStep);
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
    clearPlatePointer();

    pointerId = e.pointerId;
    mode = "drag";
    pointerX = followX = e.clientX;
    pointerY = followY = e.clientY;
    dragLastT = performance.now();
    lastT = dragLastT;
    velRotY = 0;
    velTilt = 0;

    canvas.setPointerCapture(e.pointerId);
    setCursor("grabbing");
    motionRaf = requestAnimationFrame(dragStep);
  }

  function onPointerMove(e) {
    if (mode === "drag" && e.pointerId === pointerId) {
      e.preventDefault();
      pointerX = e.clientX;
      pointerY = e.clientY;
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

    cancelMotionLoop();
    pointerX = e.clientX;
    pointerY = e.clientY;
    flushDragLag();

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
    cancelMotionLoop();
    mode = "auto";
    setCursor(null);
    startAutoSpin();
  }

  function onLostCapture() {
    if (pointerId === null || mode !== "drag") return;
    pointerId = null;
    cancelMotionLoop();
    flushDragLag();
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
        clearPlatePointer();
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
