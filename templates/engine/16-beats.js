// ---- cut on the music: beats from cfg.beats or window.BEATS (scripts/beat_grid.py → beats.js). Camera-move ARRIVALS and
// headline starts move to the nearest beat if it is within beatSnap.tol (0.15 s); a move never gets shorter than 0.25 s.
// beatSnap:false (or beats:false) turns it off. Clicks are NOT moved (the cursor path / footage would no longer match).
function snapToBeats(){const BT=C.beats===undefined?window.BEATS:C.beats;C._beats=BT&&BT.beats&&BT.beats.length?BT.beats.slice().sort((a,b)=>a-b):null;
  if(!C._beats||C.beatSnap===false)return;
  const r=Core.snapToBeats(C.cam,C.captions,C._beats,(C.beatSnap&&C.beatSnap.tol)??0.15,!(C.beatSnap&&C.beatSnap.captions===false));
  C.cam=r.cam;C.captions=r.captions;C._beatLog=r.log;}
/** beat clock: {n: beat index, k: 0..1 phase to the next beat, t0: last beat time, down: on a bar start}; null without beats */
H.beat=t=>{const B=C&&C._beats;if(!B||t<B[0])return null;let n=0;while(n<B.length-1&&B[n+1]<=t)n++;const t1=B[n+1]??B[n]+(B[n]-(B[n-1]??B[n]-0.5));
  return {n,k:H.cl((t-B[n])/(t1-B[n])),t0:B[n],down:(window.BEATS&&window.BEATS.down||[]).some(d=>Math.abs(d-B[n])<1e-3)};};
/** 1 on each beat, easing to 0 over d seconds (scale/glow accents on the music). onlyDown: bar starts only */
H.pulse=(t,d=0.25,onlyDown=false)=>{const b=H.beat(t);if(!b||(onlyDown&&!b.down))return 0;return 1-H.eo(H.p(t,b.t0,b.t0+d));};
