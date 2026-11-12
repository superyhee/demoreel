// ---- spotlight: dim + blur everything outside the focus during camera holds
function spotAt(t){
  if(C.spots&&C.spots.length){
    // chained spots: if the next spot starts within CH seconds, don't fade out/in (that flashes the whole frame) —
    // keep the dim constant and MORPH the lit box from the previous target to the next one.
    const SP=C.spots,CH=C.spotChain??0.6,MV=C.spotMorph??0.55;
    for(let i=0;i<SP.length;i++){const [a,b,sels,dim]=SP[i];const prev=SP[i-1],next=SP[i+1];
      const chainedIn=prev&&a-prev[1]<=CH,chainedOut=next&&next[0]-b<=CH;
      const end=chainedOut?next[0]:b;               // bridge the gap to the next spot
      if(t>=a&&t<end||(i===0&&false)){
        const FI=(C.spotlight&&C.spotlight.fadeIn)||0.6,FO=(C.spotlight&&C.spotlight.fadeOut)||0.4;   // light UIs: use ~1.0/0.8 + dim ≈0.3
        const kin=chainedIn?1:H.eio(H.p(t,a,a+FI)),kout=chainedOut?1:1-H.eio(H.p(t,b-FO,b));
        const m=chainedIn?H.eio(H.p(t,a,a+MV)):1;  // morph progress from prev box
        return [sels,kin*kout,dim,chainedIn&&m<1?{from:prev[2],k:m}:null];}
    }
  }
  // explicit spots own the spotlight: mixing auto (camera-hold) spots with them causes a one-frame flash at each handoff
  if(C.spots&&C.spots.length&&!(C.spotlight&&C.spotlight.autoWithSpots))return null;
  if(!C.spotlight||!C.cam.length)return null;const K=C.cam,skip=(C.spotlight.skip||['#win']);
  // auto spotlight follows camera HOLDS; between two eligible holds it MORPHS with the camera (dim stays constant → no
  // brightness "breathing" between shots); it only fades at the first/last eligible hold.
  const ok=n=>n>=0&&n<K.length-1&&JSON.stringify(K[n][1])===JSON.stringify(K[n+1][1])&&!K[n][1].some(x=>skip.includes(x))&&(K[n][2]||1)>=(C.spotlight.minScale||1.15);
  for(let i=0;i<K.length-1;i++){if(t>=K[i][0]&&t<K[i+1][0]){
    const FI=C.spotlight.fadeIn||0.6,FO=C.spotlight.fadeOut||0.4;
    if(ok(i)){const prevOk=ok(i-2)||ok(i-1),nextOk=ok(i+1)||ok(i+2);   // hold segment
      const kin=prevOk?1:H.eio(H.p(t,K[i][0],K[i][0]+FI)),kout=nextOk?1:1-H.eio(H.p(t,K[i+1][0]-FO,K[i+1][0]));return [K[i][1],kin*kout];}
    // move segment: morph from the previous hold's target to the next hold's target
    const pv=ok(i-1)?i-1:null,nx=ok(i+1)?i+1:null;
    if(pv!==null&&nx!==null)return [K[nx][1],1,undefined,{from:K[pv][1],k:H.eio(H.p(t,K[i][0],K[i+1][0]))}];
    return null;}}
  return null;}
function drawSpot(t){
  const sp=H.$('#spot'),bands=H.$$('.sb');const r=spotAt(t);
  if(!r||r[1]<=0.01){sp.style.display='none';bands.forEach(b=>b.style.display='none');return;}
  const o=C.spotlight||{},k=r[1],dim=Math.min(r[2]??o.dim??0.35,o.maxDim??0.4)*k,bl=Math.min(o.blur??1.2,o.maxBlur??1.6)*k,pad=o.pad??14,fe=o.feather??40,rad=o.radius??14,col=o.color||'10,8,16';
  let [x0,y0,x1,y1]=union(r[0]);
  if(r[3]){const [p0,q0,p1,q1]=union(r[3].from),k=r[3].k;if(p1>p0){x0=H.lerp(p0,x0,k);y0=H.lerp(q0,y0,k);x1=H.lerp(p1,x1,k);y1=H.lerp(q1,y1,k);}}
  x0-=pad;y0-=pad;x1+=pad;y1+=pad;
  // inset feather (blur fe, spread fe): ≈98 % dim at the element border (no step against the outer dim), fades to 0 at 2·fe
  // inward → expand the element by 2·fe so no target pixel is dimmed
  const E=fe*2,X=x0-E,Y=y0-E,W=x1-x0+2*E,Hh=y1-y0+2*E;
  Object.assign(sp.style,{display:'block',left:X+'px',top:Y+'px',width:W+'px',height:Hh+'px',borderRadius:(rad+fe)+'px',
    boxShadow:`0 0 0 4000px rgba(${col},${dim}),inset 0 0 ${fe}px ${fe}px rgba(${col},${dim})`});
  if(bl<0.3){bands.forEach(b=>b.style.display='none');return;}
  const m=fe*0.5,ix0=X+m,iy0=Y+m,ix1=X+W-m,iy1=Y+Hh-m,SWx=SW,SHx=SH;   // blur bands stay outside the clear area
  // each band fades out towards the clear area (mask) — a hard blur edge cuts visibly through neighbouring UI (buttons, rows)
  const F=fe,dir=['to bottom','to top','to right','to left'];
  [[0,0,SWx,iy0],[0,iy1,SWx,SHx-iy1],[0,iy0,ix0,iy1-iy0],[ix1,iy0,SWx-ix1,iy1-iy0]].forEach((q,i)=>{const b=bands[i],mk=`linear-gradient(${dir[i]},#000 calc(100% - ${F}px),transparent)`;
    Object.assign(b.style,{display:'block',left:q[0]+'px',top:q[1]+'px',width:Math.max(0,q[2])+'px',height:Math.max(0,q[3])+'px',backdropFilter:`blur(${bl.toFixed(2)}px)`,webkitBackdropFilter:`blur(${bl.toFixed(2)}px)`,
      maskImage:mk,webkitMaskImage:mk});});
}
