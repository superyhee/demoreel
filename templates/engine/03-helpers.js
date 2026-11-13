const H={};
H.$=s=>document.querySelector(s); H.$$=s=>[...document.querySelectorAll(s)];
H.cl=x=>Math.max(0,Math.min(1,x)); H.p=(t,a,b)=>H.cl((t-a)/(b-a));
H.eo=x=>1-Math.pow(1-x,3); H.eio=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
H.eio5=x=>x<.5?16*x**5:1-Math.pow(-2*x+2,5)/2;
H.back=x=>{const c=1.7;return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)};
H.lerp=(a,b,k)=>a+(b-a)*k;
H.typed=(s,k)=>s.slice(0,Math.floor(s.length*k+1e-6));
H.caret=(t,a,b)=>t>a&&t<b&&Math.floor(t*3)%2?'▍':'';
/** pop-in scale: 0 before start, overshoot to 1 */
H.pop=(t,a,d=0.35)=>{const k=H.p(t,a,a+d);return k<=0?0:H.back(k);};
/** fade+slide helper: sets opacity & translateY on el */
H.rise=(el,t,a,d=0.5,dy=20)=>{const k=H.eo(H.p(t,a,a+d));el.style.opacity=k;const y=H.settle((1-k)*dy);el.style.transform=y?`translateY(${y}px)`:'none';return k;};
/** animate an element's height from 0 to natural height (overflow must be hidden) */
H.grow=(el,k)=>{el.style.display=k<=0?'none':'';if(k<=0)return;el.style.height='auto';const h=el.offsetHeight;el.style.height=(k*h)+'px';el.style.opacity=k;};  // set inner text BEFORE calling
// ---- UI-agnostic behaviour helpers (layout + look stay yours: rebuild them from screenshots; these only animate) ----
/** element offsetTop relative to an ancestor (walks offsetParent; give the ancestor position:relative) */
H.offsetIn=(el,root)=>{let y=0;while(el&&el!==root){y+=el.offsetTop;el=el.offsetParent;}return y;};
/** reveal WITHOUT changing layout (opacity/transform only) → camera targets measured at keyframe times keep their size.
 *  o:{d:0.35,dx:0,dy:16,s:0 (start scale delta, e.g. 0.03),ease:H.eo}. Returns k 0..1 */
// H.settle: snap the last <0.5 px of an ease-out tail to 0 — a slow sub-pixel creep re-rasterizes text every frame (shimmer)
H.settle=v=>Math.abs(v)<0.5?0:v;
/** shared transform writer for reveal-style helpers: offset (dx,dy) and scale delta s shrink to 0 as k→1, settled → 'none' */
H._xf=(el,k,dx,dy,s)=>{dx=H.settle((1-k)*dx);dy=H.settle((1-k)*dy);const sc=Math.abs((1-k)*s)<0.002?1:1-(1-k)*s;
  el.style.transform=dx||dy||sc!==1?`translate(${dx}px,${dy}px) scale(${sc})`:'none';};
/** accent colour for helpers: explicit o.color, else the page's DEMO accent */
H.accent=o=>o.color||(C&&C.accent)||'#7b2ff7';
/** set innerHTML only when the string changed (per-frame callers would otherwise re-parse + re-layout every frame) */
H.html=(el,h)=>{if(el._h!==h){el.innerHTML=h;el._h=h;}};
H.reveal=(el,t,a,o={})=>{if(!el)return 0;const d=o.d??0.35,k=(o.ease||H.eo)(H.p(t,a,a+d));el.style.opacity=k;
  H._xf(el,k,o.dx||0,o.dy??16,o.s||0);return k;};
/** popover / menu / picker: in at `open`, out at `close` (layout stays). o:{d:0.2,dout:0.15,dy:-10,s:0.03}. Returns visibility k */
H.popover=(el,t,open,close,o={})=>{if(!el)return 0;const k=H.eo(H.p(t,open,open+(o.d??0.2)))*(1-H.p(t,close,close+(o.dout??0.15)));
  el.style.opacity=k;el.style.visibility=k>0?'':'hidden';H._xf(el,k,0,o.dy??-10,o.s??0.03);return k;};
/** formatted typewriter: segs = 'plain text' | [[text], [text,'b'], [text,'em'], [text,'span class="x"'], ...] → html of the first k share */
H.typedSeg=(segs,k)=>{if(typeof segs==='string')segs=[[segs]];const tot=segs.reduce((n,s)=>n+[...s[0]].length,0);let n=Math.floor(tot*k+1e-6),out='';
  for(const s of segs){const c=[...s[0]];const take=c.slice(0,Math.max(0,Math.min(c.length,n))).join('');n-=c.length;
    if(take)out+=s[1]?`<${s[1]}>${take}</${s[1].split(' ')[0]}>`:take;}return out;};
/** stream text into el between a..b (AI answers, typed prompts, drafts) with a blinking accent caret.
 *  o:{caret:true, color:accent, pre:0.1, post:0.3, placeholder:'html shown before a'} */
H.stream=(el,t,a,b,segs,o={})=>{if(!el)return 0;const k=H.p(t,a,b);
  if(t<a&&o.placeholder!=null){H.html(el,o.placeholder);return 0;}
  const c=o.caret!==false&&H.caret(t,a-(o.pre??0.1),b+(o.post??0.3));
  H.html(el,H.typedSeg(segs,k)+(c?`<span style="color:${H.accent(o)}">${c}</span>`:''));return k;};
/** one step of an agent / job trace: row reveals at t0, spinner while running, check pops at t1.
 *  el = row; o:{icon:'[data-st]' (slot for spinner/check), meta:'[data-meta]', metaText:'3 files' | n=>`${n} results`, count:8,
 *  color, ok:'#1d8a4e'}. Returns 'hidden' | 'run' | 'done' */
H.step=(el,t,t0,t1,o={})=>{if(!el)return 'hidden';H.reveal(el,t,t0,{d:0.3,dx:30,dy:0});
  const slot=el.querySelector(o.icon||'[data-st]'),meta=el.querySelector(o.meta||'[data-meta]'),done=t>=t1,ac=H.accent(o);
  if(slot)H.html(slot,done?`<span style="display:inline-flex;color:${o.ok||'#1d8a4e'};transform:scale(${H.back(H.p(t,t1,t1+0.25))})">${H.I('checkc')}</span>`:
    `<span style="display:inline-block;width:18px;height:18px;border-radius:50%;border:2.5px solid rgba(0,0,0,.12);border-top-color:${ac};transform:rotate(${t*540}deg)"></span>`);
  if(meta){const mt=o.metaText;let s='';
    if(o.count!=null&&t>t0+0.2){const n=Math.round(o.count*H.eo(H.p(t,t0+0.3,t1)));s=typeof mt==='function'?mt(n):`${n} ${mt||''}`;}
    else if(done)s=typeof mt==='function'?mt(o.count??''):(mt||'');
    meta.textContent=s?'· '+s.trim():'';}
  return t<t0?'hidden':done?'done':'run';};
/** scroll a pane by ANCHORS (chat transcripts, feeds, docs): keys=[[tStart,tEnd,anchor],...] in time order; anchor = selector |
 *  element | number (px) [, pad]. Between beats the scroll eases (eio) from the previous anchor to the next. pad (default 64) keeps the
 *  anchor below the headline pill in close-ups (≈ captionSafe / camera scale). content needs position:relative. Returns y */
H.scrollAnchor=(content,t,keys,o={})=>{if(typeof content==='string')content=H.$(content);if(!content)return 0;const pad=o.pad??64;
  const yOf=(a,pd)=>typeof a==='number'?a:Math.max(0,H.offsetIn(typeof a==='string'?content.querySelector(a)||H.$(a):a,content)-(pd??pad));
  let y=0;for(const [a,b,an,pd] of keys)y=H.lerp(y,yOf(an,pd),H.eio(H.p(t,a,b)));content.style.transform=`translateY(${-y}px)`;return y;};
// ---- hook / kinetic-type helpers (any opening style; see references/hooks.md) ----
/** kinetic type: reveal `html` chunk by chunk. Chunks = split on '|' (author-controlled, works for CJK) or on spaces.
 *  Chunks may contain <em>/<b>/<br>. o:{stagger:0.12,d:0.35,dy:24,blur:6}. Pure in t (spans are built once per html). */
H.kinetic=(el,t,a,html,o={})=>{if(!el)return 0;if(el._kin!==html){const parts=html.includes('|')?html.split('|'):html.split(/(?<=\S)\s+(?=\S)/);
    el.innerHTML=parts.map(p=>p==='<br>'?'<br>':`<span class="kin" style="display:inline-block;white-space:pre">${p}${html.includes('|')?'':' '}</span>`).join('');el._kin=html;el._kinS=[...el.querySelectorAll('.kin')];}
  const st=o.stagger??0.12,d=o.d??0.35;let last=0;el._kinS.forEach((s,i)=>{const k=H.reveal(s,t,a+i*st,{d,dy:o.dy??24});last=k;
    s.style.filter=k<1?`blur(${(1-k)*(o.blur??6)}px)`:'none';});return last;};
/** count a number from→to between a..b (eio); fmt(n) → text, e.g. n=>`${n|0} min`. Counts must come from the story, not invented metrics */
H.count=(el,t,a,b,from,to,fmt=n=>String(Math.round(n)))=>{if(!el)return 0;const k=H.eio(H.p(t,a,b));el.textContent=fmt(H.lerp(from,to,k));return k;};
/** strike-through drawn left→right from a (d s); colour defaults to currentColor. Uses a background line → no layout change */
H.strike=(el,t,a,d=0.3,color='currentColor',w=6)=>{if(!el)return 0;const k=H.eo(H.p(t,a,a+d));el.style.backgroundImage=`linear-gradient(${color},${color})`;
  el.style.backgroundRepeat='no-repeat';el.style.backgroundPosition='0 55%';el.style.backgroundSize=`${k*100}% ${w}px`;return k;};
// Lucide-style icons (24x24, stroke). Use H.I('mail') inside template strings.
H.IC={
mail:'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>',
cal:'<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
msg:'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
bell:'<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
alert:'<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4M12 17h.01"/>',
checkc:'<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
check:'<path d="M20 6 9 17l-5-5"/>',
reply:'<path d="M9 17 4 12l5-5"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/>',
timer:'<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2 2M10 2h4"/>',
pen:'<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
act:'<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
lib:'<path d="m16 6 4 14M12 6v14M8 8v12M4 4v16"/>',
zap:'<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>',
app:'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M2 9h20M6 6.5h.01M10 6.5h.01"/>',
layers:'<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/>',
flask:'<path d="M10 2v7.5L4 20a1 1 0 0 0 .9 1.5h14.2a1 1 0 0 0 .9-1.5L14 9.5V2M8.5 2h7M7 16h10"/>',
db:'<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5M3 12a9 3 0 0 0 18 0"/>',
grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
flow:'<rect x="3" y="3" width="8" height="8" rx="2"/><path d="M7 11v4a2 2 0 0 0 2 2h4"/><rect x="13" y="13" width="8" height="8" rx="2"/>',
search:'<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
spark:'<path d="M12 3l1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2z"/>',
folder:'<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9l-.8-1.2A2 2 0 0 0 7.9 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
users:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
refresh:'<path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M8 16H3v5"/>',
down:'<path d="m6 9 6 6 6-6"/>', right:'<path d="m9 18 6-6-6-6"/>', plus:'<path d="M12 5v14M5 12h14"/>',
ext:'<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
chart:'<path d="M3 3v18h18M18 17V9M13 17V5M8 17v-3"/>',
src:'<path d="m15 10 5 5-5 5"/><path d="M4 4v7a4 4 0 0 0 4 4h12"/>',
notes:'<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M9 9h1M9 13h6M9 17h6"/>',
settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
upload:'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
play:'<path d="m6 3 14 9-14 9z"/>',
plane:'<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>', code:'<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>',
};
H.I=(n,st)=>`<svg class="i" viewBox="0 0 24 24"${st?` style="${st}"`:''}>${H.IC[n]||''}</svg>`;
