function render(t){
  const FP=C.footage?updateFootage(t):[];
  // measure each camera keyframe's targets in the UI state AT THAT KEYFRAME'S TIME (scene is a pure fn of t),
  // so targets that appear later (display:none now) or grow/shrink are framed correctly.
  let Fseg=null;const camEl=H.$('#cam');
  if(camEl&&C.cam.length&&C.scene){camEl.style.transform='none';camEl.style.filter='none';
    const ks=new Set();for(const x of [t,t-1/C.fps])segOf(x).forEach(n=>ks.add(n));Fseg={};
    for(const n of ks){C.scene(measureT(n),H);Fseg[n]=fit(C.cam[n]);}}
  C.scene&&C.scene(t,H);
  const cam=H.$('#cam');
  let s=1,wi=1,wo=0;
  if(cam&&C.cam.length){
    // measure targets with identity transform (2D/3D off) so keyframes are in stage space
    cam.style.transform='none';cam.style.filter='none';
    const mmRects=C.minimap?measureMM():null;
    const F=Fseg?C.cam.map((k,n)=>Fseg[n]||null):C.cam.map(fit);
    const c=clampCam(camAt(t,F),t),c0=clampCam(camAt(t-1/C.fps,F),t-1/C.fps);
    wi=C.camIn?H.eo(H.p(t,C.camIn[0],C.camIn[1])):1; wo=C.camOut?H.eio(H.p(t,C.camOut[0],C.camOut[1])):0;
    const [fx,fy,sc,rx,ry]=c;s=sc;const V=C.view;
    const ty=(1-wi)*420-wo*60,rxx=rx+(1-wi)*28+wo*10,sc2=sc*H.lerp(1,0.82,wo);
    // IMPORTANT: 3D transforms make Chrome rasterize at 1x then upscale (blurry text).
    // Only use rotateX/Y while entering/exiting (motion hides it); holds use pure 2D -> crisp.
    const use3d=(wi<1||wo>0)&&(Math.abs(rxx)>0.05||Math.abs(ry)>0.05);
    cam.style.transform=`translate(${V.cx}px,${V.cy+ty}px)`+(use3d?` rotateX(${rxx}deg) rotateY(${ry}deg)`:'')+` scale(${sc2}) translate(${-fx}px,${-fy}px)`;
    const speed=Math.hypot(c[0]-c0[0],c[1]-c0[1])*sc+Math.abs(c[2]-c0[2])*900;
    const blur=Math.min(C.motionBlurMax??1.5,Math.max(0,speed-8)/40)+(1-wi)*12+wo*10;   // subtle; text stays legible mid-move
    cam.style.filter=blur>0.35?`blur(${blur.toFixed(2)}px)`:'none';
    cam.style.opacity=wi*(1-wo);
    H.$('#topfade').style.opacity=wi*(1-wo);
    if(C.minimap)drawMinimap(t,{cx:V.cx,cy:V.cy+ty,sc:sc2,fx,fy,wi,wo,MR:mmRects});
  }
  drawSpot(t);
  // caption: center-out reveal
  const capEl=H.$('#cap');let ch='',co=0,rv=0;
  for(const [a,b,h] of C._caps){if(t>=a&&t<b){ch=h;rv=H.eo(H.p(t,a,a+0.45));co=1-H.p(t,b-0.25,b);}}
  if(capEl.innerHTML!==ch)capEl.innerHTML=ch;capEl.style.opacity=ch?co*Math.min(1,rv*3):0;
  capEl.style.transform=`translateX(-50%) translateY(${(1-rv)*-16}px) scale(${H.lerp(0.96,1,rv)})`;
  capEl.style.clipPath=`inset(0 ${(1-rv)*50}% 0 ${(1-rv)*50}% round 999px)`;
  // cursor + ripple
  const cp=curPos(t),cu=H.$('#cursor');const pressed=C.clicks.some(x=>t>x&&t<x+0.12);
  if(cp&&wi>0.99&&wo<0.01){const a=curPos(t-0.04),b2=curPos(t+0.04),vx=a&&b2?(b2[0]-a[0])/0.08:0,tilt=H.cl(Math.abs(vx)/2400)*Math.sign(vx)*-9;
    cu.style.opacity=1;cu.style.filter='drop-shadow(0 3px 5px rgba(0,0,0,.45))';cu.style.transform=`translate(${cp[0]-4}px,${cp[1]-2}px) rotate(${tilt}deg) scale(${H.lerp(1,1.25,H.cl((s-1)/0.7))*(pressed?.84:1)})`;}else cu.style.opacity=0;
  const rp=H.$('#ripple');let ro=0;for(const x of C.clicks){const k=H.p(t,x,x+0.45);if(k>0&&k<1&&cp){ro=(1-k)*0.9;rp.style.transform=`translate(${cp[0]-35}px,${cp[1]-35}px) scale(${0.3+H.eo(k)*1.1})`;}}rp.style.opacity=ro;
  if(C.typing)drawTyping(t);if(C.notes)drawNotes(t);drawClock(t);drawTrack(t);drawSubs(t);
  C.post&&C.post(t,H);
  if(C.declutter!==false)declutter();
  return FP.length?Promise.all(FP):undefined;   // Playwright awaits this, so footage frames are decoded before capture
}
