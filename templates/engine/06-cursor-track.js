// ---- tracked cursor (real recordings): big, smooth Screen-Studio-style pointer on the REAL pointer path
// cursorTrack:{data:[[footFrame,x,y,kind]|[footFrame,null]] (scripts/cursor_track.py, footage px), footage:0,
//              size:46, glide:[0.45,0.9], clicks:[t,...] (project s), color:'#111', ring:'#fff'}
// Pre-computed once at init over the whole project timeline (pure function of t afterwards → parallel-render safe):
// rest positions are kept exactly; every move between two rests becomes one eased glide that ENDS when the real pointer
// arrived (so clicks land on time) — the real pointer must be erased from the frames (cursor_track.py erase).
let CT=null;
function initTrack(){const T=C.cursorTrack;if(!T||!C.footage)return;const F=C.footage[T.footage||0],fps=C.fps,N=Math.ceil(C.duration*fps)+1;
  const by=new Map(T.data.map(r=>[r[0],r]));const raw=[];
  for(let n=0;n<N;n++){const ft=footTime(F,n/fps),fi=Math.min(F.frames||1e9,Math.max(1,Math.floor(ft*F.fps+1e-6)+1));const r=by.get(fi);raw.push(r&&r[1]!=null?[r[1],r[2],r[3]]:null);}
  // rests = runs of ≥3 frames within 6 px of the run anchor
  const rests=[];let a=null;
  for(let n=0;n<N;n++){const r=raw[n];
    if(r&&a&&Math.abs(r[0]-a.p[0])+Math.abs(r[1]-a.p[1])<=6){a.n1=n;continue;}
    if(a&&a.n1-a.n0>=2)rests.push(a);a=r?{n0:n,n1:n,p:[r[0],r[1]],k:r[2]}:null;}
  if(a&&a.n1-a.n0>=2)rests.push(a);
  const [g0,g1]=T.glide||[0.45,0.9],pos=new Array(N).fill(null);
  rests.forEach((R,i)=>{for(let n=R.n0;n<=R.n1;n++)pos[n]=[R.p[0],R.p[1],R.k,0];
    const Q=rests[i+1];if(!Q)return;const gap=(Q.n0-R.n1)/fps;
    if(gap>(T.hideGap??3)&&raw.slice(R.n1+1,Q.n0).every(r=>!r))return;     // pointer really gone for a while → hide
    const d=Math.hypot(Q.p[0]-R.p[0],Q.p[1]-R.p[1]),G=Math.min(g1,Math.max(g0,0.3+d/1600)),s0=Math.max(R.n1,Q.n0-Math.round(G*fps));
    for(let n=R.n1+1;n<s0;n++)pos[n]=[R.p[0],R.p[1],R.k,0];
    for(let n=s0;n<Q.n0;n++){const k=H.eio((n-s0)/Math.max(1,Q.n0-s0)),dx=Q.p[0]-R.p[0],dy=Q.p[1]-R.p[1],L=d||1,arc=Math.sin(k*Math.PI)*Math.min(40,L*0.08);
      pos[n]=[R.p[0]+dx*k-dy/L*arc,R.p[1]+dy*k+dx/L*arc,'arrow',(dx/L)*Math.sin(k*Math.PI)];}});
  // snap logged click times to the moment the pointer is actually at rest (action logs are offset by easing / edits)
  T._clicks=(T.clicks||[]).map(t=>{const n=Math.round(t*fps);if(rests.some(R=>n>=R.n0&&n<=R.n1))return t;
    const R=rests.find(R=>R.n0>n-0.3*fps&&R.n0<=n+(T.snap??1.2)*fps);return R?R.n0/fps+0.06:t;});
  CT={F,pos};}
function trackCursor(t){if(!CT)return null;const n=Math.round(t*C.fps),q=CT.pos[n];if(!q)return null;
  const el=H.$(CT.F.el),r=el.getBoundingClientRect(),z=r.width/CT.F.w;
  // fade in/out at visibility edges
  let vis=1;for(let d=1;d<=6;d++){if(!CT.pos[n-d]||!CT.pos[n+d]){vis=Math.min(vis,(d-1)/6);}}
  return {x:r.left+q[0]*z,y:r.top+q[1]*z,k:q[2],tilt:q[3],z,vis};}
function drawTrack(t){const T=C.cursorTrack;if(!T)return;const c=trackCursor(t),el=H.$('#tcur'),rp=H.$('#tring');
  if(!c){el.style.opacity=0;rp.style.opacity=0;return;}
  // macOS hides the pointer while you type → fade it out around typing reveals
  if(C.camOut)c.vis*=1-H.p(t,C.camOut[0],C.camOut[0]+0.35);if(C.camIn)c.vis*=H.p(t,C.camIn[1]-0.2,C.camIn[1]+0.2);   // never on intro/end cards
  for(const Y of C.typing||[])c.vis*=1-H.cl(Math.min(H.p(t,Y.t0-0.25,Y.t0),1-H.p(t,Y.t1+0.1,Y.t1+0.35)));
  const sz=(T.size||46)*Math.pow(c.z,0.55),cl=(T._clicks||T.clicks||[]).find(x=>t>=x-0.06&&t<x+0.5);
  const press=cl!=null?1-H.cl(Math.abs(t-cl-0.03)/0.1):0;
  el.style.opacity=c.vis;el.style.width=sz+'px';el.style.height=sz+'px';
  el.style.transform=`translate(${c.x-sz*0.17}px,${c.y-sz*0.08}px) rotate(${c.tilt*-9}deg) scale(${1-0.16*press})`;
  if(cl!=null&&t>=cl){const k=H.p(t,cl,cl+0.5),R=sz*1.6*(0.35+H.eo(k)*0.9);rp.style.opacity=(1-k)*0.85*c.vis;
    rp.style.width=rp.style.height=R+'px';rp.style.transform=`translate(${c.x-R/2}px,${c.y-R/2}px)`;}else rp.style.opacity=0;}
