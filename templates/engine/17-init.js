function init(cfg){
  C=Object.assign({duration:30,fps:30,cam:[],cursor:[],clicks:[],captions:[],sfx:[],captionMax:3.2},applyAspect(cfg));
  // STILL HOLDS (default): two consecutive keyframes on the same targets = a hold → keep the first keyframe's scale/rotation.
  // A slow push-in during a hold changes the scale every frame → Chrome re-rasterizes text and snaps glyphs to whole pixels →
  // text visibly shimmers (measured 1.6 px x / 1.0 px y wobble vs 0.000 px when still). holdPush:true restores the old drift.
  if(!C.holdPush)for(let i=1;i<C.cam.length;i++){const a=C.cam[i-1],b=C.cam[i];
    if(JSON.stringify(a[1])===JSON.stringify(b[1]))C.cam[i]=[b[0],b[1],a[2],a[3],a[4]].concat(b.slice(5));}
  snapToBeats();
  // COMMERCIAL DEFAULTS (any software): short headline cards, VO subtitles picked up from subs.js (window.SUBS) if present,
  // camera framing rules on '#win' when the page has one, no minimap unless asked for.
  C._caps=C.captions.map(c=>c[3]==='hold'||!C.captionMax?c:[c[0],Math.min(c[1],c[0]+C.captionMax),c[2]]);
  if(C.subtitles===undefined&&window.SUBS&&window.SUBS.length)C.subtitles={items:window.SUBS,keywords:window.SUBS_KW||[],accent:C.accent||'#b98bff'};
  if(C.camBounds===undefined&&document.querySelector('#win'))C.camBounds='#win';
  inject();
  // narrow frames: headline cards wrap to 2 lines → measure how low the tallest one reaches instead of the landscape 140 px
  if(C.captionSafe===undefined&&C.frameRule==='fit'&&C._caps.length){const cap=H.$('#cap');let b=0;
    for(const c of C._caps){cap.innerHTML=c[2];b=Math.max(b,cap.getBoundingClientRect().bottom);}cap.innerHTML='';C.captionSafe=Math.ceil(b+20);}
  if(C.footage)initFootage();
  initSubs();initTrackDom();initTrack();if(C.notes)initNotes();initClock();if(C.typing&&C.footage)initTyping();
  // auto SFX: clicks + whoosh on every camera move between distinct keyframes
  const S=[...C.sfx];C.clicks.forEach(t=>S.push([t,'click',1]));
  if(C.cursorTrack)(C.cursorTrack._clicks||C.cursorTrack.clicks||[]).forEach(t=>S.push([t,'click',C.cursorTrack.clickGain??0.8]));
  (C.typing||[]).forEach(T=>{if(T.tick===0)return;let prev=-1;for(let f=Math.ceil(T.t0*C.fps);f<T.t1*C.fps;f++){const c=typeCount(T,f/C.fps);
    if(c!==prev&&c%2===1)S.push([f/C.fps,'tick',T.tick??0.2]);prev=c;}});
  // camera-move whooshes: sparse by default (frequent whooshes on every move feel cheap — user feedback)
  const cs=C.camSfx===undefined?{minGap:8,gain:0.2}:C.camSfx;
  if(cs&&cs!=='off'){let last=-1e9;for(let i=1;i<C.cam.length;i++){const a=C.cam[i-1],b=C.cam[i];
    if(JSON.stringify(a[1])!==JSON.stringify(b[1])&&b[0]-a[0]<1.6&&a[0]-last>=(cs.minGap??8)){S.push([a[0]+0.05,'whoosh',cs.gain??0.2]);last=a[0];}}}
  window.SFX=S.sort((x,y)=>x[0]-y[0]);window.DURATION=C.duration;window.FPS=C.fps;
  window.render=render;window.DEMO_CFG=C;window.FRAME=[SW,SH];window.DEMO_FIT=k=>fit(k);render(0);
}
window.Demo={init,H,core:Core};
if(window.DEMO)init(window.DEMO);
