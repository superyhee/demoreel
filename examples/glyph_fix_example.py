# re-render the typed prompt in PingFang SC (the AI IDE's CJK UI font) and paste it ONLY inside the erased-pointer area
import numpy as np, cv2, json, os
from PIL import Image
from playwright.sync_api import sync_playwright
lines=[("为商品详情页添加降价提醒：用户设置目标价，商品价格",1012),("低于目标价时发邮件通知，并支持一键退订。",1042)]
orig=cv2.imread('rec_orig/f00268.jpg').astype(float);er=cv2.imread('site/rec/f00268.jpg')
bg=(38,31,34);fg=(238,233,236)
html=lambda fs:f"""<html><body style="margin:0;background:rgb(34,31,38)">{''.join(f'<div style="position:absolute;left:20px;top:{20+i*60}px;font:400 {fs}px PingFang SC;color:rgb(236,233,238);white-space:nowrap">{t}</div>' for i,(t,_) in enumerate(lines))}</body></html>"""
best={}
with sync_playwright() as p:
    b=p.chromium.launch(channel='chrome');pg=b.new_page(viewport={'width':700,'height':160},device_scale_factor=2)
    for fs in np.arange(18.4,19.5,0.1):
        pg.set_content(html(fs));png=pg.screenshot();im=cv2.imdecode(np.frombuffer(png,np.uint8),1);im=cv2.resize(im,None,fx=0.5,fy=0.5,interpolation=cv2.INTER_AREA).astype(float)
        for i,(t,ytop) in enumerate(lines):
            tpl=im[20+i*60-4:20+i*60+28,16:516].astype(np.float32)
            reg=orig[ytop-14:ytop+30,1330:1900].astype(np.float32)
            r=cv2.matchTemplate(reg,tpl,cv2.TM_SQDIFF_NORMED);v,_,loc,_=cv2.minMaxLoc(r)
            if i not in best or v<best[i][0]:best[i]=(v,fs,loc,tpl)
    b.close()
tr={r[0]:r for r in json.load(open('cursor.json'))};x,y=tr[268][1],tr[268][2]
M=np.zeros(er.shape[:2],np.uint8);cv2.rectangle(M,(x-10,y-17),(x+10,y+17),255,-1)   # erased I-beam area (+pad)
out=er.copy()
for i,(v,fs,loc,tpl) in best.items():
    ytop=lines[i][1];X0,Y0=1330+loc[0],ytop-14+loc[1];h,w=tpl.shape[:2]
    canvas=out[Y0:Y0+h,X0:X0+w];m=M[Y0:Y0+h,X0:X0+w]>0
    canvas[m]=tpl[m].astype(np.uint8);print('line',i,'font',round(fs,2),'err',round(v,4),'at',X0,Y0,'patched px',m.sum())
cv2.imwrite('glyph_fixed_268.png',out)
