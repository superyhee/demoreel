"""Shared helpers for scripts that drive a DEMO page in Chrome (renderer + QA), so they all lay the page out identically."""
import os
from urllib.parse import urlencode

ASPECT_SIZE = {'16:9': (1920, 1080), '9:16': (1080, 1920), '1:1': (1080, 1080), '4:5': (1080, 1350)}   # = engine.js ASPECTS
ASPECTS = list(ASPECT_SIZE)

def page_url(page, lang, aspect=None, **extra):
    q = {'lang': lang, **({'aspect': aspect} if aspect else {}), **{k: v for k, v in extra.items() if v is not None}}
    return 'file://' + os.path.abspath(page) + '?' + urlencode(q, safe=':')

def _pin(pg, cdp, w, h, dsf=1):
    # pin the layout AND screen size: on a laptop whose screen is shorter than the frame, some Chrome instances otherwise
    # lay out at the screen height (e.g. 993) and the clipped capture repeats rows.
    pg.set_viewport_size({'width': w, 'height': h})
    cdp.send('Emulation.setDeviceMetricsOverride', {'width': w, 'height': h, 'deviceScaleFactor': dsf, 'mobile': False,
                                                     'screenWidth': w, 'screenHeight': h})

def open_page(p, page, lang, wait=800, args=(), aspect=None, dsf=1, **extra):
    """Launch Chrome and open page?lang=…[&aspect=…] at the page's own frame size (window.FRAME, set by engine.js;
    1920×1080 for legacy pages). Returns (browser, page, cdp, page_errors). Frame size: frame_size(pg)."""
    b = p.chromium.launch(channel='chrome', args=list(args))
    pg = b.new_page(viewport={'width': 1920, 'height': 1080}, screen={'width': 1920, 'height': 1080})
    cdp = pg.context.new_cdp_session(pg); _pin(pg, cdp, 1920, 1080, dsf)
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(page_url(page, lang, aspect, **extra)); _settle(pg, wait)
    w, h = frame_size(pg)
    if (w, h) != (1920, 1080):   # re-layout at the declared frame size from a clean load (init measures the layout)
        _pin(pg, cdp, w, h, dsf); errs.clear(); pg.reload(); _settle(pg, wait)
    return b, pg, cdp, errs

_READY = 'Promise.all([document.fonts.ready,...[...document.images].map(i=>i.decode().catch(()=>0))])'

def _settle(pg, wait):
    # fonts + decoded images before the first capture: a not-yet-decoded logo made early frames nondeterministic
    pg.evaluate(_READY); pg.wait_for_timeout(wait)

def frame_size(pg):
    w, h = pg.evaluate('window.FRAME||[1920,1080]'); return int(w), int(h)

def cam_segments(pg):
    """Camera keyframe pairs as (t0, t1, is_hold): a HOLD keeps the same targets, otherwise the camera moves."""
    k = pg.evaluate('((window.DEMO_CFG||{}).cam||[]).map(k=>[k[0],JSON.stringify(k[1])])')
    return [(a[0], b[0], a[1] == b[1]) for a, b in zip(k, k[1:])]
