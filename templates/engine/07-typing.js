// ---- typing reveal (hybrid): freeze the footage on the frame where the text is complete (footage map) and reveal the
// REAL text glyph by glyph by shrinking covers painted in the field's background colour (pixel-exact, any font).
// typing:[{t0,t1,footage:0,lines:[[x,y,w,h,nChars],...] (footage px; w = nChars × glyph pitch),bg:'#221f26',caret:'#fff',tick:0.2,pad:8,pauses:[i..]}]
// Pair it with a footage-map freeze: map:[...,[t0,ftBefore],[t0+1e-4,ftComplete],[t1,ftComplete],...]. Pointer resting on the text?
// erase it, then repair glyphs it covered by re-rendering the text in the UI font (see references/pitfalls.md).
function typeCount(T,t){const n=T.lines.reduce((a,l)=>a+l[4],0);if(t<=T.t0)return 0;if(t>=T.t1)return n;
  // uneven human cadence, deterministic: per-glyph weight from a hash, longer after punctuation slots (T.pauses)
  if(!T._cum){let c=[0];for(let i=0;i<n;i++){const h=Math.abs(Math.sin(i*78.233+1.7)*43758.5453)%1;c.push(c[i]+0.65+0.7*h+((T.pauses||[]).includes(i+1)?2.2:0));}T._cum=c;}
  const c=T._cum,u=H.p(t,T.t0,T.t1)*c[n];let i=0;while(i<n&&c[i+1]<=u)i++;return i;}
function initTyping(){(C.typing||[]).forEach((T,ti)=>{const F=C.footage[T.footage||0],el=H.$(F.el),box=el.parentElement;
  T.lines.forEach(([x,y,w,h],li)=>box.insertAdjacentHTML('beforeend',`<div id="ty${ti}_${li}" style="position:absolute;pointer-events:none;display:none;background:${T.bg||'#222'};top:${y/F.h*100}%;height:${h/F.h*100}%"></div>`));
  box.insertAdjacentHTML('beforeend',`<div id="tyc${ti}" style="position:absolute;pointer-events:none;display:none;width:${2/F.w*100}%;background:${T.caret||'#fff'};border-radius:1px"></div>`);});}
function drawTyping(t){(C.typing||[]).forEach((T,ti)=>{const F=C.footage[T.footage||0],on=t>=T.t0-0.001&&t<T.t1;const c=typeCount(T,t);let o=0,cx=null,cl=null;
  T.lines.forEach(([x,y,w,h,n],li)=>{const d=H.$(`#ty${ti}_${li}`),k=H.cl(c-o);const typed=Math.max(0,Math.min(n,c-o));
    const left=x+typed/n*w;d.style.display=on?'block':'none';d.style.left=left/F.w*100+'%';d.style.width=Math.max(0,x+w+(T.pad??8)-left)/F.w*100+'%';   // pad also hides the frozen frame's own caret
    if(typed>0||li===0){cx=left;cl=[y,h];}o+=n;});
  const cu=H.$(`#tyc${ti}`);cu.style.display=on&&cl?'block':'none';
  if(cl){cu.style.left=(cx+1)/F.w*100+'%';cu.style.top=(cl[0]+2)/F.h*100+'%';cu.style.height=(cl[1]-4)/F.h*100+'%';}});}
