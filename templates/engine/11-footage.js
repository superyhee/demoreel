// ---- footage (real screen recordings): image-sequence layer driven by a time map, + hotspots + speed badge
function footTime(F,t){const m=F.map||[[F.start||0,0],[(F.start||0)+1e6,1e6]];
  if(t<=m[0][0])return m[0][1];for(let i=0;i<m.length-1;i++)if(t<=m[i+1][0])return H.lerp(m[i][1],m[i+1][1],H.p(t,m[i][0],m[i+1][0]));return m[m.length-1][1];}
function footRate(F,t){const m=F.map;if(!m)return 1;for(let i=0;i<m.length-1;i++)if(t>=m[i][0]&&t<m[i+1][0])return (m[i+1][1]-m[i][1])/Math.max(1e-6,m[i+1][0]-m[i][0]);return 0;}
function updateFootage(t){const ps=[];let badge=0;
  for(const F of C.footage){const el=H.$(F.el);if(!el)continue;const ft=footTime(F,t);
    const idx=Math.min(F.frames||1e9,Math.max(1,Math.floor(ft*F.fps+1e-6)+1));const src=F.src+String(idx).padStart(5,'0')+'.'+(F.ext||'jpg');
    if(el._src!==src){el._src=src;el.src=src;ps.push(el.decode().catch(()=>{}));}
    if(F.badges){for(const [a,b,r] of F.badges)if(t>=a&&t<b)badge=Math.max(badge,r);}   // pre-edited footage: explicit ⏩ windows
    else if(F.speedBadge!==false){const r=footRate(F,t);if(r>=1.5)badge=Math.max(badge,r);}}
  C._badge=badge;const b=H.$('#speed'),K=C.footage.map(F=>F.clock).find(Boolean);
  if(b&&K&&!C.clock){const [sa,sb]=K.show||[0,1e9],c=clockAt(K,t),vis=Math.min(H.p(t,sa,sa+0.4),1-H.p(t,sb-0.4,sb));b.style.opacity=vis;
    const spin=`<span style="display:inline-block;width:22px;height:22px;margin-right:12px;vertical-align:-3px;border-radius:50%;border:3px solid rgba(255,255,255,.25);border-top-color:${C.accent||'#b98bff'};transform:rotate(${t*360*1.2}deg)"></span>`;
    const ok=`<span style="color:#4ade80;margin-right:10px">✓</span>`;
    b.innerHTML=(c.done?ok+(K.done||'完成'):spin+(K.label||'工作中'))+` <span style="font-variant-numeric:tabular-nums;font-family:ui-monospace,Menlo,monospace;margin-left:8px">${mmss(c.e)}</span>`+(badge&&!c.done?`<span style="opacity:.6;font-size:24px;margin-left:12px">${Math.round(badge)}× 延时</span>`:'');}
  else if(b){b.style.opacity=badge?1:0;if(badge)b.textContent='⏩ ×'+Math.round(badge);}
  return ps;}
function initFootage(){for(const F of C.footage){const el=H.$(F.el);if(!el)continue;const box=el.parentElement;
  if(getComputedStyle(box).position==='static')box.style.position='relative';
  // hotspots live in the IMAGE's footage px: % of the parent only works when the image fills it — otherwise (image inset /
  // letterboxed inside a larger panel) place them from the image's own offset box, or the camera frames the wrong area
  const fills=!el.offsetLeft&&!el.offsetTop&&el.offsetWidth===box.clientWidth&&el.offsetHeight===box.clientHeight;
  const pos=fills?(x,y,w,h)=>`left:${x/F.w*100}%;top:${y/F.h*100}%;width:${w/F.w*100}%;height:${h/F.h*100}%`
    :(x,y,w,h)=>{const kx=el.offsetWidth/F.w,ky=el.offsetHeight/F.h;return `left:${el.offsetLeft+x*kx}px;top:${el.offsetTop+y*ky}px;width:${w*kx}px;height:${h*ky}px`;};
  for(const [id,[x,y,w,h]] of Object.entries(F.hotspots||{}))box.insertAdjacentHTML('beforeend',`<div id="${id.replace('#','')}" style="position:absolute;${pos(x,y,w,h)};visibility:hidden;pointer-events:none"></div>`);}
  if(!H.$('#speed'))H.$('#stage').insertAdjacentHTML('beforeend','<div id="speed" style="position:absolute;left:48px;bottom:44px;z-index:22;opacity:0;background:rgba(20,18,28,.88);color:#fff;font:700 34px -apple-system,sans-serif;padding:12px 26px;border-radius:999px;box-shadow:0 10px 30px rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.2)"></div>');}
