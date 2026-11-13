// ---- core: the camera / beat math as PURE functions (plain numbers in, plain numbers out; no DOM, no config globals).
// The engine's DOM layer measures rects and passes them in; tests/engine_core.test.js exercises these directly in Node.
// Keep the arithmetic order as is: frames are compared bit-for-bit (md5) across refactors.
const Core = (() => {
  const cl = x => Math.max(0, Math.min(1, x));
  const p = (t, a, b) => cl((t - a) / (b - a));
  const lerp = (a, b, k) => a + (b - a) * k;
  const eio = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;

  /** two keyframes on the same targets = a camera HOLD */
  const sameT = (a, b) => JSON.stringify(a[1]) === JSON.stringify(b[1]);

  /** time at which keyframe n is measured: its own time, except a hold, which is measured at the hold's END —
   *  content that streams / slides in during the hold is framed in its settled layout, and both ends agree. */
  function measureT(K, n, holdPush) {
    if (holdPush) return K[n][0];
    while (n < K.length - 1 && sameT(K[n], K[n + 1])) n++;
    return K[n][0];
  }

  /** [i, j]: the keyframe pair around t ([0,0] before the first, [last,last] after the last) */
  function segOf(K, t) {
    if (t <= K[0][0]) return [0, 0];
    if (t >= K[K.length - 1][0]) return [K.length - 1, K.length - 1];
    let i = 0;
    while (t > K[i + 1][0]) i++;
    return [i, i + 1];
  }

  /** scale at which the bounds rect r covers the whole frame (no empty canvas) */
  const fillScale = (r, SW, SH) => Math.max(SW / r.width, SH / r.height);

  /** Hard clamp: keep the viewport inside the app (r = bounds rect). No scale-dependent blending — that blending made the
   *  centre oscillate when the scale hovered around the fill scale → visible jitter on zoom-outs.
   *  'fit' frames let the app float vertically (the caption band wins over filling the frame). */
  function clampToBounds(c, r, V, SW, SH, frameRule) {
    const s = c[2];
    const cx = (r.right - r.left) <= SW / s ? (r.left + r.right) / 2
      : Math.min(Math.max(c[0], r.left + V.cx / s), r.right - (SW - V.cx) / s);
    const cy = frameRule === 'fit' ? c[1]
      : (r.bottom - r.top) <= SH / s ? (r.top + r.bottom) / 2
      : Math.min(Math.max(c[1], r.top + V.cy / s), r.bottom - (SH - V.cy) / s);
    return [cx, cy, c[2], c[3], c[4]];
  }

  /** Frame one keyframe k = [t, sels, maxScale, rotX, rotY] → camera [cx, cy, scale, rotX, rotY].
   *  tgt    [x0,y0,x1,y1] union of the target rects (stage px, camera at identity)
   *  bounds the camBounds rect ({left,top,right,bottom,width,height}) or null (no framing rules)
   *  wide   the keyframe targets the bounds itself → WIDE shot
   *  o      config: view, frameRule, wideFill, fitMinZoom, fitMaxZoom, captionSafe, bottomSafe, maxZoom
   *  WIDE      the app takes wideFill (90 %) of the frame with equal margins
   *  CLOSE-UP  'fill' (landscape): the app fills the frame; 'fit' (portrait/square): the TARGET fills the view width at
   *            ≥ fitMinZoom (UI text stays readable on a phone), a target wider than the view keeps its left edge.
   *            Either way the target stays below the caption band (captionSafe) and off the bottom edge. */
  function frameShot(tgt, k, bounds, wide, o, SW, SH) {
    const V = o.view, [x0, y0, x1, y1] = tgt, r = bounds;
    let s = Math.min(k[2], o.maxZoom || 99, V.w / Math.max(1, x1 - x0), V.h / Math.max(1, y1 - y0));
    let cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    if (r && wide) {
      s = (o.wideFill ?? 0.9) * Math.min(SW / r.width, SH / r.height) * (k[2] < 1 ? k[2] : 1);
      cx = (r.left + r.right) / 2;
      cy = (r.top + r.bottom) / 2 + (V.cy - SH / 2) / s;
    } else if (r && k[2] > 1.05) {
      if (o.frameRule === 'fit') {
        s = Math.max(o.fitMinZoom ?? 1.3, Math.min(V.w / Math.max(1, x1 - x0), V.h / Math.max(1, y1 - y0), o.fitMaxZoom ?? 2.2));
        if ((x1 - x0) * s > V.w) cx = x0 + (V.w / 2 - 24) / s;   // UIs read left→right: crop the right
      } else s = Math.max(s, fillScale(r, SW, SH) * 1.002);
      const top = o.captionSafe ?? 140, bot = o.bottomSafe ?? 24;
      cy = Math.min(cy, y0 + (V.cy - top) / s);
      cy = Math.max(cy, y1 - (SH - bot - V.cy) / s);
      const cc = clampToBounds([cx, cy, s], r, V, SW, SH, o.frameRule);
      cx = cc[0]; cy = cc[1];
    }
    return [cx, cy, s, k[3] || 0, k[4] || 0];
  }

  /** per frame, only BETWEEN two close-ups: never zoom out below the close-up floor (no U-shaped zoom = no wobble) and
   *  keep the viewport inside the app. Close↔wide moves just interpolate their (already clamped) keyframes. */
  function clampBetweenCloseUps(c, r, o, SW, SH) {
    const fill = o.frameRule === 'fit' ? (o.fitMinZoom ?? 1.3) / 1.002 : fillScale(r, SW, SH);
    return clampToBounds([c[0], c[1], Math.max(c[2], fill * 1.002), c[3], c[4]], r, o.view, SW, SH, o.frameRule);
  }

  /** Camera path between two shots: van Wijk & Nuij "smooth and efficient zooming and panning" (same math as
   *  d3.interpolateZoom). Near targets → mostly a pan; far targets → a gentle, perceptually constant zoom-out/in.
   *  State (fx,fy,s) ↔ (ux,uy,w) with w = SW/s (visible world width). Returns {S: path length, at(k) → [fx,fy,s]}. */
  function zoomPath(a, b, rho, SW) {
    const ux0 = a[0], uy0 = a[1], w0 = SW / a[2], ux1 = b[0], uy1 = b[1], w1 = SW / b[2];
    const dx = ux1 - ux0, dy = uy1 - uy0, d2 = dx * dx + dy * dy, r2 = rho * rho;
    if (d2 < 1e-6) {
      const S = Math.log(w1 / w0) / rho;
      return { S: Math.abs(S), at: k => [ux0 + k * dx, uy0 + k * dy, SW / (w0 * Math.exp(rho * k * S))] };
    }
    const d1 = Math.sqrt(d2),
      b0 = (w1 * w1 - w0 * w0 + r2 * r2 * d2) / (2 * w0 * r2 * d1),
      b1 = (w1 * w1 - w0 * w0 - r2 * r2 * d2) / (2 * w1 * r2 * d1),
      R0 = Math.log(Math.sqrt(b0 * b0 + 1) - b0), R1 = Math.log(Math.sqrt(b1 * b1 + 1) - b1), S = (R1 - R0) / rho;
    return { S: Math.abs(S), at: k => {
      const sk = k * S, c = Math.cosh(R0), u = w0 / (r2 * d1) * (c * Math.tanh(rho * sk + R0) - Math.sinh(R0));
      return [ux0 + u * dx, uy0 + u * dy, SW / (w0 * c / Math.cosh(rho * sk + R0))];
    } };
  }

  /** camera at time t from the framed keyframes F (F[n] = frameShot of K[n]).
   *  o: holdPush, camPath ('linear'), camRho (1.25), cutS. STILL HOLD (default): a hold keeps its first framing even if the
   *  target's layout changes meanwhile — the camera must not drift. Very long jumps (S > cutS, or K[j][5].cut) CUT. */
  function camAt(K, F, t, o, SW) {
    const [i, j] = segOf(K, t);
    if (i === j) return F[i];
    const raw = p(t, K[i][0], K[j][0]), same = sameT(K[i], K[j]);
    if (same && !o.holdPush) return F[i];
    if (same || o.camPath === 'linear') {
      const k = same ? raw : eio(raw);
      return F[i].map((v, n) => lerp(v, F[j][n], k));
    }
    const zp = zoomPath(F[i], F[j], o.camRho ?? 1.25, SW);
    const cut = (K[j][5] && K[j][5].cut) || (o.cutS && zp.S > o.cutS);
    if (cut) return raw < 1 ? F[i] : F[j];
    const k = eio(raw), q = zp.at(k);
    return [q[0], q[1], q[2], lerp(F[i][3], F[j][3], k), lerp(F[i][4], F[j][4], k)];
  }

  /** nearest beat to t (B sorted ascending, non-empty) */
  function nearBeat(B, t) {
    let lo = 0, hi = B.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (B[m] <= t) lo = m; else hi = m; }
    return Math.abs(B[lo] - t) <= Math.abs(B[hi] - t) ? B[lo] : B[hi];
  }

  /** Cut on the music: move camera-move ARRIVALS (and headline starts unless captions:false) to the nearest beat within tol.
   *  A move never gets shorter than 0.25 s; holds are not moved. Returns {cam, captions, log} (inputs are not mutated). */
  function snapToBeats(cam, captions, B, tol, snapCaptions) {
    const K = cam.slice(), log = [];
    for (let i = 1; i < K.length; i++) {
      if (sameT(K[i - 1], K[i])) continue;
      const t = K[i][0], b = nearBeat(B, t);
      if (Math.abs(b - t) > tol || Math.abs(b - t) < 1e-3 || b < K[i - 1][0] + 0.25 || (K[i + 1] && b > K[i + 1][0] - 0.25)) continue;
      K[i] = [b].concat(K[i].slice(1)); log.push(['cam', t, b]);
    }
    const caps = !snapCaptions ? captions : captions.map(c => {
      const b = nearBeat(B, c[0]);
      if (Math.abs(b - c[0]) > tol || Math.abs(b - c[0]) < 1e-3) return c;
      log.push(['caption', c[0], b]);
      return [b, c[1] + b - c[0]].concat(c.slice(2));
    });
    return { cam: K, captions: caps, log };
  }

  return { cl, p, lerp, eio, sameT, measureT, segOf, fillScale, clampToBounds, frameShot, clampBetweenCloseUps,
           zoomPath, camAt, nearBeat, snapToBeats };
})();
