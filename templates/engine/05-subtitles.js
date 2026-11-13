// ---- dynamic subtitles (VO-synced, word highlight, keyword emphasis, auto position away from the focus)
// subtitles:{items:[{t0,t1,words:[{t,text}]}], keywords:['Spec',...], accent:'#b98bff', size:40, band:190, mute:[[a,b]]}
function initTrackDom(){if(!C.cursorTrack||H.$('#tcur'))return;const T=C.cursorTrack;
  H.$('#stage').insertAdjacentHTML('beforeend',`<div id="tring" style="position:absolute;left:0;top:0;z-index:23;pointer-events:none;opacity:0;border-radius:50%;border:3px solid ${T.ringColor||'rgba(185,139,255,.95)'};background:${T.ringFill||'rgba(185,139,255,.18)'}"></div>
  <svg id="tcur" viewBox="0 0 24 24" style="position:absolute;left:0;top:0;z-index:24;pointer-events:none;opacity:0;overflow:visible;transform-origin:17% 8%;filter:drop-shadow(0 3px 5px rgba(0,0,0,.45))"><path d="M4 2l16 9.5-7 1.6 4.2 7.4-2.8 1.5-4.2-7.4L5 19z" fill="${T.color||'#111'}" stroke="${T.stroke||'#fff'}" stroke-width="1.6" stroke-linejoin="round"/></svg>`);}
function initSubs(){const S=C.subtitles;if(!S||H.$('#subs'))return;const ac=S.accent||'#b98bff',narrow=SW<SH*1.2;
  // narrow frames (9:16, 1:1): phrases wrap instead of running off the frame
  H.$('#stage').insertAdjacentHTML('beforeend',`<div id="subs" style="position:absolute;left:50%;bottom:${subBottom()}px;z-index:22;max-width:${narrow?SW-80:Math.min(1500,SW-120)}px;
    padding:12px 26px;border-radius:16px;background:rgba(12,10,18,.74);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
    box-shadow:0 10px 30px rgba(0,0,0,.35);font:600 ${S.size||40}px/1.35 'PingFang SC',-apple-system,sans-serif;color:#fff;
    text-align:center;white-space:${narrow?'normal':'nowrap'};opacity:0;letter-spacing:.5px"></div>`);
  const st=document.createElement('style');st.textContent=`#subs .w{transition:none;display:inline-block}#subs .w.f{opacity:.42}#subs .w.k{color:${ac};font-weight:700}
    #subs .w.c{color:#fff;text-shadow:0 0 18px ${ac}cc}#subs .w.k.c{color:${ac};text-shadow:0 0 18px ${ac}}`;document.head.appendChild(st);}
// bottom margin: 56 px on landscape; on portrait above the ~16 % that Reels / TikTok / Shorts cover with their own UI
const subBottom=()=>C.subtitles.bottom??(SH>SW?Math.round(SH*0.16):56);
function subFocusRect(t){   // the rect the viewer is looking at: active spot target, else camera hold target
  const sp=spotAt(t);let sels=sp?sp[0]:null;if(!sels&&C.cam.length){const [i,j]=segOf(t);sels=C.cam[i][1];}
  if(!sels)return null;const [x0,y0,x1,y1]=union(sels);return x1>x0?[x0,y0,x1,y1]:null;}
function drawSubs(t){const S=C.subtitles;if(!S)return;const el=H.$('#subs');
  // mute:[[a,b],...] — skip where the same words are already big on screen (hook title, logo/name card, end card)
  if((S.mute||[]).some(([a,b])=>t>=a&&t<b)){el.style.opacity=0;return;}let it=null,idx=-1;
  for(let k=0;k<S.items.length;k++){const x=S.items[k];if(t>=x.t0-0.18&&t<x.t1+0.22){it=x;idx=k;break;}}
  if(!it){el.style.opacity=0;return;}
  if(el._i!==idx){el._i=idx;const kw=(S.keywords||[]);el.innerHTML=it.words.map((w,n)=>{const isK=kw.some(k=>w.text.includes(k));
      return `<span class="w${isK?' k':''}" data-n="${n}">${w.text.replace(/ /g,'&nbsp;')}</span>`;}).join('');}
  const ws=el.children;let cur=-1;for(let n=0;n<it.words.length;n++)if(t>=it.words[n].t-0.04)cur=n;
  for(let n=0;n<ws.length;n++){const c=ws[n].classList;c.toggle('f',n>cur);c.toggle('c',n===cur);
    const k=n===cur?H.eo(H.p(t,it.words[n].t-0.04,it.words[n].t+0.14)):0;ws[n].style.transform=n===cur?`translateY(${-2*k}px) scale(${1+0.04*k})`:'';}
  const kin=H.eo(H.p(t,it.t0-0.18,it.t0+0.1)),kout=1-H.p(t,it.t1,it.t1+0.22);el.style.opacity=Math.min(kin,kout);
  // position: always the bottom band (default, like broadcast subtitles); position:'auto' dodges a focus target there
  const fr=S.position==='auto'?subFocusRect(t):null,band=S.band||190,top=!!(fr&&fr[3]>SH-band&&fr[1]>140);
  const ty=(1-kin)*14;el.style.top=top?(C.captionSafe??140)+'px':'auto';el.style.bottom=top?'auto':subBottom()+'px';
  el.style.transform=`translateX(-50%) translateY(${top?-ty:ty}px)`;}
