// ---- work clock for sped-up AI work (replaces "⏩ ×N"): real elapsed time keeps counting, speed shown small
// footage[i].clock:{segs:[[t0,t1,rawA,speed],...] (project s → recording s), zero:rawStart, stopAt:rawEnd|null,
//                   label:'Agent 工作中', done:'完成', show:[tA,tB]}
function clockAt(K,t){let raw=null;for(const [a,b,ra,sp] of K.segs)if(t>=a&&t<b){raw=ra+(t-a)*sp;}
  if(raw==null){const L=K.segs.filter(s=>s[1]<=t).pop();raw=L?L[2]+(L[1]-L[0])*L[3]:K.zero;}
  const e=Math.max(0,Math.min(raw,K.stopAt??1e12)-K.zero);return {e,done:K.stopAt!=null&&raw>=K.stopAt};}
const mmss=e=>`${String(Math.floor(e/60)).padStart(2,'0')}:${String(Math.floor(e%60)).padStart(2,'0')}`;
function initClock(){if(!C.clock||H.$('#speed'))return;
  H.$('#stage').insertAdjacentHTML('beforeend','<div id="speed" style="position:absolute;left:48px;bottom:44px;z-index:22;opacity:0;background:rgba(20,18,28,.88);color:#fff;font:700 30px -apple-system,sans-serif;padding:12px 26px;border-radius:999px;box-shadow:0 10px 30px rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.2)"></div>');}
// C.clock:{segs:[[t0,t1,simA,speed],...], zero, stopAt, label, done, show:[a,b], speedLabel:'× 延时'}  (simulated UIs: segs map
// project time → story time, e.g. [[54.8,70,0,162]] = 41 min of agent work shown in 15 s)
function drawClock(t){const K=C.clock,b=H.$('#speed');if(!K||!b)return;const [sa,sb]=K.show||[0,1e9],c=clockAt(K,t);
  b.style.opacity=Math.min(H.p(t,sa,sa+0.4),1-H.p(t,sb-0.4,sb));let sp=0;for(const [a,bb,,v] of K.segs)if(t>=a&&t<bb)sp=v;
  const spin=`<span style="display:inline-block;width:22px;height:22px;margin-right:12px;vertical-align:-3px;border-radius:50%;border:3px solid rgba(255,255,255,.25);border-top-color:${C.accent||'#b98bff'};transform:rotate(${t*360*1.2}deg)"></span>`;
  b.innerHTML=(c.done?`<span style="color:#4ade80;margin-right:10px">✓</span>`+(K.done||'完成'):spin+(K.label||'工作中'))+` <span style="font-variant-numeric:tabular-nums;font-family:ui-monospace,Menlo,monospace;margin-left:8px">${mmss(c.e)}</span>`+(sp>=1.5&&!c.done?`<span style="opacity:.6;font-size:24px;margin-left:12px">${Math.round(sp)}${K.speedLabel||'× 延时'}</span>`:'');}
