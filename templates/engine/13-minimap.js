// ---- minimap ("you are here"): schematic of the whole window + current viewport box
function measureMM(){const M=C.minimap,w=H.$(M.target||'#win').getBoundingClientRect();
  return {win:w,panels:(M.panels||[]).map(([sel,lab])=>{const e=H.$(sel);const r=e?e.getBoundingClientRect():null;return r&&r.width>4&&r.height>4?[r,lab]:null;}).filter(Boolean)};}
function drawMinimap(t,c){const M=C.minimap,mm=H.$('#mm');const R=c.MR,W=M.w||300,hh=W*R.win.height/R.win.width,col=M.color||'#b98bff';
  const show=c.sc>=(M.minScale||1.12)&&c.wi>=1&&c.wo<=0;mm._k=H.lerp(mm._k||0,show?1:0,0.25);if(t<0.05)mm._k=0;
  // deterministic fade: based on scale distance instead of history
  const k=H.cl((c.sc-(M.minScale||1.12))/0.12)*(c.wi>=1&&c.wo<=0?1:0);
  const pos=M.pos||[SW-W-32,46];Object.assign(mm.style,{left:pos[0]+'px',top:pos[1]+'px',width:W+'px',height:hh+'px',opacity:k,
    background:'rgba(18,16,24,.88)',border:'1px solid rgba(255,255,255,.16)',borderRadius:'10px',boxShadow:'0 12px 30px rgba(0,0,0,.45)',transform:`translateY(${(1-k)*-8}px)`});
  const sx=W/R.win.width,sy=hh/R.win.height;let html='';
  for(const [r,lab] of R.panels){html+=`<div style="position:absolute;left:${(r.left-R.win.left)*sx+2}px;top:${(r.top-R.win.top)*sy+2}px;width:${r.width*sx-4}px;height:${r.height*sy-4}px;background:rgba(255,255,255,.07);border-radius:4px;font-size:11px;color:rgba(255,255,255,.55);display:flex;align-items:center;justify-content:center;overflow:hidden;white-space:nowrap">${lab}</div>`;}
  // viewport (stage) mapped back into window space
  const inv=(X,Y)=>[(X-c.cx)/c.sc+c.fx,(Y-c.cy)/c.sc+c.fy];const [a0,b0]=inv(0,0),[a1,b1]=inv(SW,SH);
  const vx0=Math.max(0,(a0-R.win.left)*sx),vy0=Math.max(0,(b0-R.win.top)*sy),vx1=Math.min(W,(a1-R.win.left)*sx),vy1=Math.min(hh,(b1-R.win.top)*sy);
  html+=`<div style="position:absolute;left:${vx0}px;top:${vy0}px;width:${Math.max(6,vx1-vx0)}px;height:${Math.max(6,vy1-vy0)}px;border:2px solid ${col};background:${col}22;border-radius:4px;box-shadow:0 0 12px ${col}88"></div>`;
  if(mm._h!==html){mm.innerHTML=html;mm._h=html;}}
