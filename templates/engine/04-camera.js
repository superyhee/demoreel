// ---- camera + cursor: the DOM side of the framing rules (measure rects, hand them to Core)
let C=null,SW=1920,SH=1080;   // config + output frame size (C.size); the authored world inside #cam keeps its own px
function inject(){
  const st=H.$('#stage');
  const add=(html)=>st.insertAdjacentHTML('beforeend',html);
  if(!H.$('#topfade'))add('<div id="topfade" class="abs"></div>');
  if(!H.$('#cap'))add('<div id="cap" class="abs"></div>');
  if(!H.$('#ripple'))add('<div id="ripple" class="abs"></div>');
  if(!H.$('#spot')){const z='position:absolute;left:0;top:0;pointer-events:none;';add(`<div id="spot" style="${z}z-index:17;display:none"></div>`+[0,1,2,3].map(i=>`<div class="sb" id="sb${i}" style="${z}z-index:16;display:none"></div>`).join(''));}
  if(C.minimap&&!H.$('#mm'))add('<div id="mm" style="position:absolute;z-index:21;pointer-events:none;opacity:0"><div id="mmv" style="position:absolute"></div></div>');
  if(!H.$('#cursor'))add('<svg id="cursor" class="abs" viewBox="0 0 24 24"><path d="M4 2l16 9.5-7 1.6 4.2 7.4-2.8 1.5-4.2-7.4L5 19z" fill="#111" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>');
}
/** bounding box [x0,y0,x1,y1] of the visible elements matching sels (stage px) */
function union(sels){
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  for(const s of sels){const e=H.$(s);if(!e)continue;const r=e.getBoundingClientRect();if(!r.width&&!r.height)continue;
    x0=Math.min(x0,r.left);y0=Math.min(y0,r.top);x1=Math.max(x1,r.right);y1=Math.max(y1,r.bottom);}
  return [x0,y0,x1,y1];}
/** the camBounds rect (the app window), or null when the page has no framing bounds */
function boundsRect(){if(!C.camBounds)return null;const B=H.$(C.camBounds);return B?B.getBoundingClientRect():null;}
const isWide=n=>!!(C.camBounds&&C.cam[n]&&C.cam[n][1].includes(C.camBounds));
/** frame keyframe k in the CURRENT layout (render() puts the scene into the keyframe's state first) */
function fit(k){return Core.frameShot(union(k[1]),k,boundsRect(),!!(C.camBounds&&k[1].includes(C.camBounds)),C,SW,SH);}
/** per-frame clamp: only between two close-ups (see Core.clampBetweenCloseUps) */
function clampCam(c,t){const r=boundsRect();if(!r)return c;const [i,j]=Core.segOf(C.cam,t);
  if(isWide(i)||isWide(j))return c;return Core.clampBetweenCloseUps(c,r,C,SW,SH);}
const measureT=n=>Core.measureT(C.cam,n,C.holdPush);
const segOf=t=>Core.segOf(C.cam,t);
const camAt=(t,F)=>Core.camAt(C.cam,F,t,C,SW);
// cursor path: eased, slightly arced moves between keyframes ('#sel' = the element's centre, [x,y] = stage px)
function rectC(sel){const r=H.$(sel).getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2];}
function curPos(t){const K=C.cursor;if(!K.length||t<K[0][0]||t>K[K.length-1][0])return null;
  for(let i=0;i<K.length-1;i++){const [a,A]=K[i],[b,B]=K[i+1];if(t<=b){const k=H.eio(H.p(t,a,b));const pa=typeof A==='string'?rectC(A):A,pb=typeof B==='string'?rectC(B):B;
    const dx=pb[0]-pa[0],dy=pb[1]-pa[1],n=Math.hypot(dx,dy)||1,arc=Math.sin(k*Math.PI)*Math.min(60,n*0.12);
    return [H.lerp(pa[0],pb[0],k)-dy/n*arc,H.lerp(pa[1],pb[1],k)+dx/n*arc];}}}
