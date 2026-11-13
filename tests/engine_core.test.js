// Unit tests for the engine's pure camera / beat math (templates/engine/02-core.js). No browser needed.
// run: node --test tests/
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

// same realm as the test (deepStrictEqual compares prototypes); the module is a plain script declaring `const Core`
const Core = new Function(fs.readFileSync(path.join(__dirname, '..', 'templates', 'engine', '02-core.js'), 'utf8') + '\nreturn Core;')();

const near = (a, b, eps = 1e-6, msg) => assert.ok(Math.abs(a - b) <= eps, `${msg || ''} ${a} ≉ ${b}`);
const rect = (left, top, width, height) => ({ left, top, width, height, right: left + width, bottom: top + height });

// the starter template's geometry: 16:9 frame, app window 1560×850 at (180,190), landscape view
const SW = 1920, SH = 1080;
const WIN = rect(180, 190, 1560, 850);
const VIEW16 = { cx: 960, cy: 620, w: 1640, h: 780 };
const fill = { view: VIEW16, frameRule: 'fill' };
/** where a world point lands on screen for camera c (engine: translate(V.cx,V.cy) scale(s) translate(-fx,-fy)) */
const screen = (c, V, x, y) => [V.cx + (x - c[0]) * c[2], V.cy + (y - c[1]) * c[2]];

test('segOf: clamps before the first / after the last keyframe, else the surrounding pair', () => {
  const K = [[1], [2], [4]];
  assert.deepEqual(Core.segOf(K, 0), [0, 0]);
  assert.deepEqual(Core.segOf(K, 1), [0, 0]);
  assert.deepEqual(Core.segOf(K, 1.5), [0, 1]);
  assert.deepEqual(Core.segOf(K, 2), [0, 1]);
  assert.deepEqual(Core.segOf(K, 3), [1, 2]);
  assert.deepEqual(Core.segOf(K, 9), [2, 2]);
});

test('measureT: a hold is measured at its END keyframe (settled layout); holdPush measures at its own time', () => {
  const K = [[1, ['#a']], [3, ['#a']], [5, ['#a']], [6, ['#b']]];
  assert.equal(Core.measureT(K, 0), 5);
  assert.equal(Core.measureT(K, 1), 5);
  assert.equal(Core.measureT(K, 3), 6);
  assert.equal(Core.measureT(K, 0, true), 1);
});

test('frameShot WIDE: the app takes 90 % of the frame, centred with equal side margins', () => {
  const c = Core.frameShot([WIN.left, WIN.top, WIN.right, WIN.bottom], [0, ['#win'], 1], WIN, true, fill, SW, SH);
  near(c[2], 0.9 * Math.min(SW / 1560, SH / 850));
  const [l, t] = screen(c, VIEW16, WIN.left, WIN.top), [r, b] = screen(c, VIEW16, WIN.right, WIN.bottom);
  near(l, SW - r, 1e-6, 'left/right margins');
  near(t, SH - b, 1e-6, 'top/bottom margins');
  near(r - l, 0.9 * Math.min(SW / 1560, SH / 850) * 1560, 1e-6);
});

test('frameShot CLOSE-UP fill: no empty canvas, target below the caption band, viewport inside the app', () => {
  const tgt = [520, 300, 1700, 520];   // a list block near the top of the window
  const c = Core.frameShot(tgt, [0, ['#list'], 1.5], WIN, false, fill, SW, SH);
  assert.ok(c[2] >= Core.fillScale(WIN, SW, SH), 'fills the frame');
  const [, ty] = screen(c, VIEW16, tgt[0], tgt[1]);
  const [wl, wt] = screen(c, VIEW16, WIN.left, WIN.top), [wr, wb] = screen(c, VIEW16, WIN.right, WIN.bottom);
  assert.ok(wl <= 1e-6 && wt <= 1e-6 && wr >= SW - 1e-6 && wb >= SH - 1e-6, `app covers the frame ${[wl, wt, wr, wb]}`);
  // the caption band wins unless the app edge stops the camera (then the target sits as low as the bounds allow)
  assert.ok(ty >= 140 - 1e-6 || Math.abs(wt) < 1e-6, `target top ${ty} under the caption band`);
});

test('frameShot CLOSE-UP fit (portrait): ≥ 1.3× and a target wider than the view keeps its left edge', () => {
  const V = { cx: 540, cy: 960, w: 1080 * 0.92, h: 1920 * 0.6 };
  const o = { view: V, frameRule: 'fit', captionSafe: 300 };
  const wide = [520, 300, 1700, 520];   // 1180 px wide → wider than the view at 1.3×
  const c = Core.frameShot(wide, [0, ['#list'], 1.5], WIN, false, o, 1080, 1920);
  near(c[2], 1.3);
  const [lx] = screen(c, V, wide[0], wide[1]);
  near(lx, V.cx - (V.w / 2 - 24), 1e-6, 'left edge 24 px inside the view');
  const small = [600, 600, 800, 660];  // small target → zoomed until it fills the width, capped at 2.2×
  const c2 = Core.frameShot(small, [0, ['#btn'], 1.5], WIN, false, o, 1080, 1920);
  near(c2[2], 2.2);
});

test('frameShot without bounds: plain fit of the target into the view, capped by maxScale', () => {
  const c = Core.frameShot([100, 100, 300, 200], [0, ['#x'], 1.4, 2, -3], null, false, fill, SW, SH);
  assert.deepEqual(c, [200, 150, 1.4, 2, -3]);
});

test('clampToBounds: never shows outside the app; a viewport larger than the app centres it', () => {
  const c = Core.clampToBounds([0, 0, 1.5, 0, 0], WIN, VIEW16, SW, SH, 'fill');
  const [l, t] = screen(c, VIEW16, WIN.left, WIN.top);
  near(l, 0); near(t, 0);
  const z = Core.clampToBounds([0, 0, 0.5, 0, 0], WIN, VIEW16, SW, SH, 'fill');
  near(z[0], (WIN.left + WIN.right) / 2); near(z[1], (WIN.top + WIN.bottom) / 2);
  const f = Core.clampToBounds([0, 7, 1.5, 0, 0], WIN, VIEW16, SW, SH, 'fit');
  assert.equal(f[1], 7, "'fit' leaves the vertical position alone");
});

test('clampBetweenCloseUps: the zoom never dips below the close-up floor between two close-ups', () => {
  const c = Core.clampBetweenCloseUps([960, 600, 0.8, 0, 0], WIN, fill, SW, SH);
  near(c[2], Core.fillScale(WIN, SW, SH) * 1.002);
  const p = Core.clampBetweenCloseUps([540, 900, 1.0, 0, 0], WIN, { view: VIEW16, frameRule: 'fit' }, SW, SH);
  near(p[2], 1.3);
});

test('zoomPath: starts and ends on the keyframes; the length grows with distance', () => {
  const a = [500, 400, 1.4], b = [1400, 700, 1.2];
  const zp = Core.zoomPath(a, b, 1.25, SW);
  zp.at(0).forEach((v, i) => near(v, a[i], 1e-6));
  zp.at(1).forEach((v, i) => near(v, b[i], 1e-6));
  assert.ok(Core.zoomPath(a, [2400, 700, 1.2], 1.25, SW).S > zp.S);
  const pure = Core.zoomPath([500, 400, 1], [500, 400, 2], 1.25, SW);   // same centre → pure zoom
  near(pure.at(1)[2], 2, 1e-9);
});

test('camAt: still holds, eased moves, cuts', () => {
  const K = [[0, ['#a']], [2, ['#a']], [4, ['#b']]];
  const F = [[100, 100, 1.5, 0, 0], [100, 100, 1.5, 0, 0], [800, 500, 1.2, 0, 0]];   // hold ends frame alike (measureT)
  assert.deepEqual(Core.camAt(K, F, 1, {}, SW), F[0], 'hold keeps the first framing (no drift)');
  const mid = Core.camAt(K, F, 3, {}, SW);
  assert.ok(mid[0] > 100 && mid[0] < 800 && mid[1] > 100 && mid[1] < 500, 'move is between the shots');
  assert.deepEqual(Core.camAt(K, F, 3, { cutS: 1e-3 }, SW), F[1], 'long jump → cut: previous shot until arrival');
  assert.deepEqual(Core.camAt(K, F, 5, {}, SW), F[2]);
  const G = [[100, 100, 1.5, 0, 0], [300, 100, 1.5, 0, 0], F[2]];
  near(Core.camAt(K, G, 1, { holdPush: true }, SW)[0], 200, 1e-9, 'holdPush drifts linearly');
  assert.deepEqual(Core.camAt(K, G, 1, {}, SW), G[0], 'still hold ignores a differently framed hold end');
});

test('nearBeat: nearest, ties go to the earlier beat, clamps at the ends', () => {
  const B = [1, 2, 3];
  assert.equal(Core.nearBeat(B, 2.4), 2);
  assert.equal(Core.nearBeat(B, 2.5), 2);
  assert.equal(Core.nearBeat(B, 2.6), 3);
  assert.equal(Core.nearBeat(B, -5), 1);
  assert.equal(Core.nearBeat(B, 99), 3);
});

test('snapToBeats: arrivals snap within tol, holds stay, moves stay ≥ 0.25 s, inputs untouched', () => {
  const B = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4];
  const cam = [[0, ['#a']], [1.1, ['#b']], [2.9, ['#b']], [3.05, ['#c']]];
  const caps = [[1.42, 2.4, 'x'], [3.3, 4, 'y']];
  const r = Core.snapToBeats(cam, caps, B, 0.15, true);
  assert.equal(r.cam[1][0], 1, 'arrival 1.1 → beat 1.0');
  assert.equal(r.cam[2][0], 2.9, 'hold end is not moved');
  assert.equal(r.cam[3][0], 3.05, 'snapping to 3.0 would leave a < 0.25 s move');
  assert.equal(r.captions[0][0], 1.5, 'caption start snaps');
  near(r.captions[0][1] - r.captions[0][0], 2.4 - 1.42, 1e-9, 'caption duration kept');
  assert.equal(r.captions[1], caps[1], 'outside tol → unchanged');
  assert.equal(cam[1][0], 1.1, 'input cam not mutated');
  assert.deepEqual(r.log.map(l => l[0]), ['cam', 'caption']);
  assert.equal(Core.snapToBeats(cam, caps, B, 0.15, false).captions, caps, 'captions:false');
});
