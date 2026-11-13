// ---- callouts on real footage: animated highlight box + label pill, tracked in footage px (follows the camera)
// notes:[{t0,t1,box:[x,y,w,h] (footage px) | sel:'#id'|['#a','#b'] (page elements, union),label:'…',side:'top'|'bottom'|'left'|'right',pad,color}]
function initNotes(){(C.notes||[]).forEach((N,i)=>{const c=N.color||(C.accent||'#b98bff');
  H.$('#stage').insertAdjacentHTML('beforeend',`<div id="dnB${i}" style="position:absolute;left:0;top:0;z-index:21;pointer-events:none;opacity:0;border:3px solid ${c};border-radius:10px;box-shadow:0 0 0 4px ${c}33,0 0 26px ${c}88"></div>
  <div id="dnL${i}" style="position:absolute;left:0;top:0;z-index:21;pointer-events:none;opacity:0;white-space:nowrap;background:${c};color:#fff;font:700 26px 'PingFang SC',-apple-system,sans-serif;padding:8px 18px;border-radius:999px;box-shadow:0 10px 26px rgba(0,0,0,.4)">${N.label||''}</div>`);});}
function drawNotes(t){(C.notes||[]).forEach((N,i)=>{const b=H.$("#dnB"+i),l=H.$("#dnL"+i);
  const on=H.p(t,N.t0,N.t0+0.45),off=1-H.p(t,N.t1-0.3,N.t1),vis=t>=N.t0&&t<N.t1?Math.min(1,off):0;
  if(!vis){b.style.opacity=0;l.style.opacity=0;return;}
  let X,Y,W,Hh;const P=N.pad??6,k=H.eo(on);
  if(N.sel){const rs=[].concat(N.sel).map(q=>H.$(q)).filter(Boolean).map(e=>e.getBoundingClientRect()).filter(r=>r.width>0);if(!rs.length){b.style.opacity=0;l.style.opacity=0;return;}
    const x0=Math.min(...rs.map(r=>r.left)),y0=Math.min(...rs.map(r=>r.top)),x1=Math.max(...rs.map(r=>r.right)),y1=Math.max(...rs.map(r=>r.bottom));X=x0-P;Y=y0-P;W=x1-x0+2*P;Hh=y1-y0+2*P;}
  else{const F=C.footage[N.footage||0],r=H.$(F.el).getBoundingClientRect(),z=r.width/F.w,[x,y,w,h]=N.box;X=r.left+x*z-P;Y=r.top+y*z-P;W=w*z+2*P;Hh=h*z+2*P;}
  b.style.left=X+'px';b.style.top=Y+'px';b.style.width=W+'px';b.style.height=Hh+'px';
  // default: the whole box fades + settles in (a still caught mid-way never shows a half-drawn border); draw:'wipe' = old left→right draw-on
  if(N.draw==='wipe'){b.style.opacity=vis;b.style.clipPath=`inset(-12px ${(1-k)*100}% -12px -12px)`;}
  else{b.style.opacity=vis*k;b.style.transform=k<1?`scale(${1.04-0.04*k})`:'none';}
  const kl=H.eo(H.p(t,N.t0+0.25,N.t0+0.6)),lw=l.offsetWidth,lh=l.offsetHeight,sd=N.side||'top';
  const lx=sd==='left'?X-lw-14:sd==='right'?X+W+14:X,ly=sd==='top'?Y-lh-12:sd==='bottom'?Y+Hh+12:Y+Hh/2-lh/2;
  l.style.opacity=vis*kl;l.style.transform=`translate(${lx}px,${ly+(1-kl)*10}px) scale(${0.9+0.1*kl})`;});}
