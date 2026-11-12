/* demo-engine.js — deterministic, frame-accurate animation engine for software demo videos.
 *
 * The page must define window.DEMO = {...} BEFORE loading this file (or call Demo.init(cfg) later).
 * The renderer calls window.render(t) for every frame (t in seconds); nothing depends on wall-clock time.
 *
 * Config (all optional except scene):
 *   duration: 30, fps: 30
 *   view: {cx:960, cy:620, w:1640, h:780}   // safe area the camera fits targets into (below the caption)
 *   cam:   [[t, ['#sel', ...], maxScale, rotX, rotY], ...]   // camera keyframes; targets measured live
 *   camIn:  [a,b]  window entry (rise + 3D tilt + blur)      camOut: [a,b] window exit
 *   cursor:[[t, '#sel' | [x,y]], ...]  cursor path keyframes (stage coords for points)
 *   clicks:[t, ...]                     click moments (ripple + press + 'click' sfx)
 *   captions:[[a,b,'html with <em>accent</em>'], ...]
 *   sfx:  [[t,'type',gain], ...]        extra sound events (pop|click|tick|whoosh|swish|suck|boom|chime|shimmer)
 *   scene(t, H): your per-frame state function (runs BEFORE the camera is measured)
 *   post(t, H):  runs after camera/cursor (e.g. end cards that sit outside #cam)
 *   spotlight: {dim:.55, blur:2.2, pad:14, feather:40, radius:14, color:'10,8,16', minScale:1.15, skip:['#win']}
 *              auto-focus the camera's HOLD targets (dim+blur outside, feathered); off while the camera moves
 *   spots: [[a,b,['#sel'],dim?], ...]  explicit spotlight windows (override auto). Spots that follow each other within
 *              spotChain (0.6 s) are CHAINED: the lit box morphs (spotMorph 0.55 s) and the dim never drops (no flash)
 *   footage: [{el:'#rec', src:'rec/f', ext:'jpg', fps:30, frames:N, w:1280, h:800, map:[[projT,footT],...],
 *              hotspots:{'#hs-input':[x,y,w,h]}, speedBadge:true}]  real recordings (see footage_prep.py);
 *              map = piecewise-linear project→footage seconds (slope>1 = sped up + '⏩ ×N' badge, equal footT = freeze)
 *   subtitles: {items:[{t0,t1,words:[{t,text}]}], keywords:[..], accent, size, band}  VO-synced subtitles (scripts/subtitle_marks.py):
 *              phrase fade/slide, current word highlighted, upcoming words dimmed, keywords in accent; auto-moves to the top
 *              (position:'bottom' default; 'auto' moves them below the caption band when the focus target sits at the bottom).
 *   camSfx: 'off' | {minGap:8, gain:0.2}   auto whoosh on camera moves (default sparse; 'off' = only scene whooshes you add)
 *   camBounds: '#win'   framing rules: shots on the bounds selector = WIDE (app ≈ wideFill 90 % of screen, equal margins);
 *                       other zoomed shots = CLOSE-UP (fill 100 %, viewport clamped to the app, target kept below captionSafe px)
 *   maxZoom: 1.4        global cap on camera scale (keep context; let spotlight do the focusing)
 *   camRho: 1.25        camera path between shots = van Wijk–Nuij optimal zoom/pan (near → pan, far → gentle zoom-out). Lower = flatter
 *   cutS: 1.6           optional: if the path length S exceeds this, CUT instead of flying (or per shot: cam[i][5]={cut:true})
 *   motionBlurMax: 1.5  px; camPath:'linear' restores plain interpolation. (viaWide/viaCenter are superseded and ignored)
 *   NOTE: keyframe targets are measured in the scene state at the keyframe's own time (scene must be pure in t)
 *   minimap: {target:'#win', panels:[['#side','侧栏'],...], w:300, pos:[x,y], color, minScale:1.12}  'you are here' map while zoomed
 *
 * Required DOM: #stage containing #cam (wrapping the app window). Engine injects #cap, #cursor, #ripple, #topfade.
 */
(function(){
