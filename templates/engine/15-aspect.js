// ---- output aspect: cfg.size [W,H] or ?aspect=16:9|9:16|1:1|4:5 (URL wins, so one page renders every cut).
// cfg.aspects:{'9:16':{cam:[…],captions:[…],view:{…},…}} overrides any config key for that aspect only.
const ASPECTS={'16:9':[1920,1080],'9:16':[1080,1920],'1:1':[1080,1080],'4:5':[1080,1350]};
function applyAspect(cfg){const q=new URLSearchParams(location.search).get('aspect'),key=q&&ASPECTS[q]?q:null;
  const size=key?ASPECTS[key]:(cfg.size||[1920,1080]),ar=key||Object.keys(ASPECTS).find(k=>ASPECTS[k][0]*size[1]===ASPECTS[k][1]*size[0])||'custom';
  cfg=Object.assign({},cfg,(cfg.aspects||{})[ar]||{});[SW,SH]=size;
  const land=SW>=SH*1.2,view=land?{cx:SW/2,cy:SH*620/1080,w:SW*1640/1920,h:SH*780/1080}:{cx:SW/2,cy:SH*0.5,w:SW*0.92,h:SH*0.6};
  for(const e of [document.documentElement,document.body,H.$('#stage')])if(e){e.style.width=SW+'px';e.style.height=SH+'px';}
  document.body.classList.add('ar-'+ar.replace(':','x'));document.body.style.setProperty('--W',SW+'px');document.body.style.setProperty('--H',SH+'px');
  return Object.assign({size,aspect:ar,view,frameRule:land?'fill':'fit'},cfg);}
