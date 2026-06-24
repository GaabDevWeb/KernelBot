/* =============================================================
   Reusable low-poly globe renderer.
   -------------------------------------------------------------
   A UV grid of quad "plates" is projected to 2D each frame
   (rotation + perspective). The caller animates the exposed
   `state` / `faces` (e.g. GSAP drives the entrance formation),
   or asks the engine to self-spin (e.g. the tiny "thinking" globe).

   createGlobe(canvas, {
     sizeTo: "window" | "self",  // viewport, or the canvas' own CSS box
     variant: "hero" | "thinking", // compact accent globe for loading state
     formed:  boolean,            // start fully assembled (no fly-in)
     spin:    boolean,            // self-rotate every frame
     spinSpeed: number,           // radians per second when spin is on
     particles: boolean,          // faint background sparkles
   }) -> { state, faces, resize, stop }
   ============================================================= */

export function createGlobe(canvas, opts = {}) {
  const {
    sizeTo = "window",
    variant = "hero",
    formed = false,
    spin = false,
    spinSpeed = 0.7,
    particles: withParticles = true,
  } = opts;

  const isThinking = variant === "thinking";
  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const ctx = canvas.getContext("2d");

  let W = 0;
  let H = 0;
  let DPR = 1;

  function resize() {
    DPR = Math.min(window.devicePixelRatio || 1, isThinking ? 2 : 2);
    if (sizeTo === "self") {
      W = canvas.clientWidth || (isThinking ? 40 : 32);
      H = canvas.clientHeight || (isThinking ? 40 : 32);
    } else {
      W = window.innerWidth;
      H = window.innerHeight;
    }
    canvas.width = W * DPR;
    canvas.height = H * DPR;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }

  /* ---------- geometry ---------- */
  const LAT = isThinking ? 4 : 5;
  const LON = isThinking ? 9 : 10;

  const state = {
    rotY: -0.6,
    tilt: -0.42,
    cx: 0.5,
    cy: 0.5,
    scale: 1,
  };

  const grid = [];
  for (let i = 0; i <= LAT; i++) {
    const theta = (i / LAT) * Math.PI;
    const row = [];
    for (let j = 0; j <= LON; j++) {
      const phi = (j / LON) * Math.PI * 2;
      row.push({
        x: Math.sin(theta) * Math.cos(phi),
        y: Math.cos(theta),
        z: Math.sin(theta) * Math.sin(phi),
      });
    }
    grid.push(row);
  }

  const faces = [];
  for (let i = 0; i < LAT; i++) {
    for (let j = 0; j < LON; j++) {
      const corners = [
        grid[i][j],
        grid[i][j + 1],
        grid[i + 1][j + 1],
        grid[i + 1][j],
      ];
      const dir = randomUnitVec();
      const mag = 2.6 + Math.random() * 2.4;
      const offset = { x: dir.x * mag, y: dir.y * mag, z: dir.z * mag };
      faces.push({ corners, offset, p: formed ? 1 : 0 });
    }
  }

  function randomUnitVec() {
    const u = Math.random() * 2 - 1;
    const t = Math.random() * Math.PI * 2;
    const s = Math.sqrt(1 - u * u);
    return { x: s * Math.cos(t), y: u, z: s * Math.sin(t) };
  }

  const particles = withParticles
    ? Array.from({ length: 46 }, () => ({
        x: Math.random(),
        y: Math.random(),
        z: 0.3 + Math.random() * 0.7,
        r: 0.6 + Math.random() * 1.6,
        tw: Math.random() * Math.PI * 2,
      }))
    : [];

  /* ---------- projection ---------- */
  const FOCAL = isThinking ? 2.4 : 2.7;
  const PLATE_SCALE = isThinking ? 0.88 : 0.9;

  const PALETTE = isThinking
    ? { fill: [185, 28, 28], stroke: [220, 100, 100], vertex: [245, 200, 200] }
    : { fill: [220, 222, 228], stroke: [235, 237, 242], vertex: [248, 249, 252] };

  function rotate(p) {
    const cy = Math.cos(state.rotY);
    const sy = Math.sin(state.rotY);
    let x = p.x * cy + p.z * sy;
    let z = -p.x * sy + p.z * cy;
    const cx = Math.cos(state.tilt);
    const sx = Math.sin(state.tilt);
    const y = p.y * cx - z * sx;
    z = p.y * sx + z * cx;
    return { x, y, z };
  }

  function project(rp, cxPix, cyPix, Rpix) {
    const zc = Math.min(rp.z, FOCAL - 0.8);
    const persp = FOCAL / (FOCAL - zc);
    return {
      x: cxPix + rp.x * Rpix * persp,
      y: cyPix + rp.y * Rpix * persp,
      z: rp.z,
    };
  }

  /* ---------- render loop ---------- */
  let rafId = 0;
  let running = true;
  let startTime = performance.now();
  let prev = startTime;

  function frame(now) {
    rafId = requestAnimationFrame(frame);
    if (!running) return;

    const dt = (now - prev) / 1000;
    prev = now;
    if (spin && !prefersReducedMotion) {
      state.rotY += (isThinking ? spinSpeed * 0.85 : spinSpeed) * dt;
    }

    const t = now - startTime;
    ctx.clearRect(0, 0, W, H);

    const sizeMin = Math.min(W, H);
    const baseR = sizeMin * (isThinking ? 0.4 : 0.28) * state.scale;
    const cornerR = isThinking
      ? Math.max(0.28, sizeMin * 0.032)
      : 7;
    const lineW = isThinking
      ? Math.max(0.28, sizeMin / 88)
      : 1;
    const vertexR = isThinking
      ? Math.max(0.35, sizeMin / 48)
      : 1.6;
    const cxPix = state.cx * W;
    const bob = isThinking
      ? Math.sin(t * 0.0012) * 0.008 * H
      : Math.sin(t * 0.0006) * 0.012 * H;
    const cyPix = state.cy * H + bob;

    if (isThinking) drawThinkingGlow(t, cxPix, cyPix, baseR);
    if (withParticles) drawParticles(t);

    const drawList = [];
    for (const f of faces) {
      if (f.p <= 0.001) continue;
      const lerp = Math.min(1, Math.max(0, f.p));
      const k = 1 - f.p;

      const proj = [];
      let zSum = 0;
      const rotated = [];
      for (const c of f.corners) {
        const pos = {
          x: c.x + f.offset.x * k,
          y: c.y + f.offset.y * k,
          z: c.z + f.offset.z * k,
        };
        const rp = rotate(pos);
        rotated.push(rp);
        zSum += rp.z;
        proj.push(project(rp, cxPix, cyPix, baseR));
      }

      const facing = faceFacing(rotated);
      const plate = buildPlate(proj, cornerR);
      drawList.push({
        proj,
        shape: plate.pts,
        radius: plate.r,
        z: zSum / proj.length,
        facing,
        op: lerp,
      });
    }

    drawList.sort((a, b) => a.z - b.z);

    for (const d of drawList) {
      const front = (d.facing + 1) / 2;
      const fillMul = isThinking ? 0.06 : 0.18;
      const a = d.op * (0.03 + front * fillMul);
      roundedPath(d.shape, d.radius);
      const [fr, fg, fb] = PALETTE.fill;
      ctx.fillStyle = `rgba(${fr}, ${fg}, ${fb}, ${a})`;
      ctx.fill();
    }

    ctx.globalCompositeOperation = isThinking ? "source-over" : "lighter";
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    for (const d of drawList) {
      const front = (d.facing + 1) / 2;
      const edgeMul = isThinking ? 0.38 : 0.6;
      const edgeA = d.op * (0.08 + front * edgeMul);

      roundedPath(d.shape, d.radius);
      ctx.lineWidth = lineW;
      const [sr, sg, sb] = PALETTE.stroke;
      ctx.strokeStyle = `rgba(${sr}, ${sg}, ${sb}, ${edgeA})`;
      if (!isThinking) {
        ctx.shadowColor = "rgba(255, 255, 255, 0.85)";
        ctx.shadowBlur = front > 0.5 ? 8 : 0;
      }
      ctx.stroke();
      ctx.shadowBlur = 0;

      const vtxThreshold = isThinking ? 0.92 : 0.55;
      if (!isThinking && front > vtxThreshold) {
        const [vr, vg, vb] = PALETTE.vertex;
        for (const v of d.proj) {
          ctx.beginPath();
          ctx.arc(v.x, v.y, vertexR, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${vr}, ${vg}, ${vb}, ${d.op * 0.55})`;
          ctx.fill();
        }
      }
    }
    ctx.globalCompositeOperation = "source-over";

    if (isThinking) drawThinkingOrbit(t, cxPix, cyPix, baseR);
  }

  function drawThinkingGlow(t, cxPix, cyPix, baseR) {
    const pulse = 0.5 + 0.5 * Math.sin(t * 0.0028);
    const glowR = baseR * (1.18 + pulse * 0.05);
    const grd = ctx.createRadialGradient(cxPix, cyPix, 0, cxPix, cyPix, glowR);
    grd.addColorStop(0, `rgba(185, 28, 28, ${0.14 + pulse * 0.06})`);
    grd.addColorStop(0.6, `rgba(185, 28, 28, 0.04)`);
    grd.addColorStop(1, "rgba(185, 28, 28, 0)");
    ctx.fillStyle = grd;
    ctx.beginPath();
    ctx.arc(cxPix, cyPix, glowR, 0, Math.PI * 2);
    ctx.fill();
  }

  function drawThinkingOrbit(t, cxPix, cyPix, baseR) {
    const orbitR = baseR * 1.05;
    ctx.globalCompositeOperation = "source-over";
    for (let i = 0; i < 2; i++) {
      const angle = t * 0.0014 + (i * Math.PI * 2) / 2;
      const x = cxPix + Math.cos(angle) * orbitR;
      const y = cyPix + Math.sin(angle) * orbitR * 0.35;
      const tw = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * 0.003 + i));
      ctx.beginPath();
      ctx.arc(x, y, 0.55, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(164, 196, 228, ${0.22 * tw})`;
      ctx.fill();
    }
  }

  function buildPlate(proj, cornerR) {
    const pts = dedupe(proj);
    let cx = 0;
    let cy = 0;
    for (const p of pts) {
      cx += p.x;
      cy += p.y;
    }
    cx /= pts.length;
    cy /= pts.length;

    const inset = pts.map((p) => ({
      x: cx + (p.x - cx) * PLATE_SCALE,
      y: cy + (p.y - cy) * PLATE_SCALE,
    }));

    let minEdge = Infinity;
    for (let i = 0; i < inset.length; i++) {
      const a = inset[i];
      const b = inset[(i + 1) % inset.length];
      minEdge = Math.min(minEdge, Math.hypot(a.x - b.x, a.y - b.y));
    }
    const r = Math.max(isThinking ? 0.35 : 1.2, Math.min(cornerR, minEdge * (isThinking ? 0.28 : 0.42)));
    return { pts: inset, r };
  }

  function dedupe(pts) {
    const out = [];
    for (const p of pts) {
      const last = out[out.length - 1];
      if (!last || Math.hypot(p.x - last.x, p.y - last.y) > 0.6) out.push(p);
    }
    if (out.length > 2) {
      const a = out[0];
      const b = out[out.length - 1];
      if (Math.hypot(a.x - b.x, a.y - b.y) <= 0.6) out.pop();
    }
    return out;
  }

  function roundedPath(pts, r) {
    const n = pts.length;
    ctx.beginPath();
    if (n < 3) {
      if (n > 0) ctx.moveTo(pts[0].x, pts[0].y);
      if (n > 1) ctx.lineTo(pts[1].x, pts[1].y);
      return;
    }
    ctx.moveTo((pts[n - 1].x + pts[0].x) / 2, (pts[n - 1].y + pts[0].y) / 2);
    for (let i = 0; i < n; i++) {
      const prevPt = pts[(i + n - 1) % n];
      const cur = pts[i];
      const next = pts[(i + 1) % n];

      const ax = prevPt.x - cur.x, ay = prevPt.y - cur.y;
      const bx = next.x - cur.x, by = next.y - cur.y;
      const la = Math.hypot(ax, ay);
      const lb = Math.hypot(bx, by);
      if (la < 1e-4 || lb < 1e-4) {
        ctx.lineTo(cur.x, cur.y);
        continue;
      }

      const cos = Math.min(1, Math.max(-1, (ax * bx + ay * by) / (la * lb)));
      const tanHalf = Math.tan(Math.acos(cos) / 2);
      const rc = Math.min(r, Math.min(la, lb) * 0.5 * tanHalf);
      if (!(rc > 0.05)) {
        ctx.lineTo(cur.x, cur.y);
        continue;
      }
      ctx.arcTo(cur.x, cur.y, next.x, next.y, rc);
    }
    ctx.closePath();
  }

  function faceFacing(rp) {
    const ax = rp[2].x - rp[0].x, ay = rp[2].y - rp[0].y, az = rp[2].z - rp[0].z;
    const bx = rp[3].x - rp[1].x, by = rp[3].y - rp[1].y, bz = rp[3].z - rp[1].z;
    const nx = ay * bz - az * by;
    const ny = az * bx - ax * bz;
    const nz = ax * by - ay * bx;
    const len = Math.hypot(nx, ny, nz) || 1;
    return -(nz / len);
  }

  function drawParticles(t) {
    ctx.globalCompositeOperation = "lighter";
    for (const p of particles) {
      const tw = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * 0.001 + p.tw));
      ctx.beginPath();
      ctx.arc(p.x * W, p.y * H, p.r * p.z, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(200, 202, 210, ${0.06 * tw * p.z})`;
      ctx.fill();
    }
    ctx.globalCompositeOperation = "source-over";
  }

  /* ---------- boot ---------- */
  resize();
  if (sizeTo === "window") {
    window.addEventListener("resize", resize);
  }
  rafId = requestAnimationFrame(frame);

  function stop() {
    running = false;
    cancelAnimationFrame(rafId);
    if (sizeTo === "window") window.removeEventListener("resize", resize);
  }

  return { state, faces, resize, stop };
}
