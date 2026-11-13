// ---- declutter (default on): never more than 3 overlay layers. When a callout / card / clock is on screen, the headline card
// (then the persona pill) fades out in proportion — smooth, stateless, so parallel rendering stays deterministic.
function declutter(){const op=e=>e?+(e.style.opacity||getComputedStyle(e).opacity):0;
  const focus=Math.max(0,...[...document.querySelectorAll('.card,[id^="dnB"]')].map(op),op(H.$('#speed')));
  const layers=['#cap','#subs','#speed','#persona','#mm'].map(q=>op(H.$(q))).filter(v=>v>0.3).length+[...document.querySelectorAll('.card,[id^="dnB"]')].filter(e=>op(e)>0.3).length;
  if(layers<=3||focus<=0)return;let n=layers;
  for(const q of ['#cap','#persona']){if(n<=3)break;const e=H.$(q);if(e&&op(e)>0.3){e.style.opacity=op(e)*(1-focus);n--;}}}
