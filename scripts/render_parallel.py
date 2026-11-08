#!/usr/bin/env python3
"""Parallel segmented render: N Chrome workers each render a contiguous frame range of the DEMO page and pipe
screenshots straight into their own ffmpeg (no PNGs on disk); segments are then concatenated losslessly.

usage: render_parallel.py <page.html> <out_video.mp4> [--lang zh] [--workers N] [--crf 17] [--preset medium]
                          [--frames-dir DIR]   # optional: also keep PNG frames (for flicker_check / re-encode)
Writes <out_dir>/sfx_<lang>.json (window.SFX) like render_frames.py. Feed the mp4 to mix.sh as the first arg.

Why it is safe to split: the page's render(t) is a pure function of t (engine contract), so any frame range can be
rendered independently. Each segment starts with a keyframe and all segments share encoder params → concat -c copy.
Throughput is bound by screenshot capture (~7 fps per worker on M2 Max); workers scale until CPU/GPU saturate.
"""
import argparse, os, sys, subprocess, tempfile, time, json, base64, shutil

def worker(page, lang, f0, f1, seg_path, crf, preset, frames_dir):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=['--window-size=1920,1080', '--disable-gpu-vsync', '--disable-frame-rate-limit'] + os.environ.get('RP_CHROME_ARGS', '').split())
        pg = b.new_page(viewport={'width': 1920, 'height': 1080}, screen={'width': 1920, 'height': 1080})
        cdp = pg.context.new_cdp_session(pg)
        # pin the layout AND screen size before navigation: on a laptop whose screen is shorter than 1080 px, some
        # Chrome instances otherwise lay out at the screen height (e.g. 993) and the clipped capture repeats rows.
        cdp.send('Emulation.setDeviceMetricsOverride', {'width': 1920, 'height': 1080, 'deviceScaleFactor': 1, 'mobile': False,
                                                         'screenWidth': 1920, 'screenHeight': 1080})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('file://' + os.path.abspath(page) + f'?lang={lang}'); pg.wait_for_timeout(800)
        if errs: sys.exit('page error: ' + errs[0])
        fps = pg.evaluate('window.FPS||30')
        ih = pg.evaluate('innerHeight')
        if ih != 1080: sys.exit(f'viewport is {ih}px high, expected 1080 — refusing to render corrupted frames')
        CLIP = {'x': 0, 'y': 0, 'width': 1920, 'height': 1080, 'scale': 1}
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'image2pipe', '-framerate', str(fps), '-i', '-',
                               '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', str(crf), '-preset', preset,
                               '-x264-params', 'keyint=60:min-keyint=1', '-threads', os.environ.get('RP_X264_THREADS', '2'), '-r', str(fps), seg_path], stdin=subprocess.PIPE)
        try:
            for f in range(f0, f1):
                pg.evaluate(f'render({f / fps})')
                png = base64.b64decode(cdp.send('Page.captureScreenshot', {'format': 'png', 'optimizeForSpeed': True, 'clip': CLIP, 'captureBeyondViewport': False})['data'])
                ff.stdin.write(png)
                if frames_dir:
                    with open(os.path.join(frames_dir, f'f{f:04d}.png'), 'wb') as fh: fh.write(png)
        except BrokenPipeError:
            pass   # ffmpeg died; its own stderr above has the reason, the return code below reports it
        except BaseException:
            ff.kill(); raise   # page/CDP error: don't leave ffmpeg waiting on stdin
        finally:
            try: ff.stdin.close()
            except BrokenPipeError: pass
            ff.wait(); b.close()
        if ff.returncode: sys.exit(f'ffmpeg failed (exit {ff.returncode}) for segment {seg_path} at frames {f0}-{f1}')

def main():
    a = argparse.ArgumentParser()
    a.add_argument('page'); a.add_argument('out'); a.add_argument('--lang', default='zh')
    a.add_argument('--workers', type=int, default=max(2, min(6, (os.cpu_count() or 4) // 2)))   # 6 ≈ sweet spot on M2 Max (34 fps)
    a.add_argument('--crf', type=int, default=17); a.add_argument('--preset', default='medium')
    a.add_argument('--frames-dir'); a.add_argument('--limit', type=int, help='render only the first N frames (benchmark)'); a.add_argument('--_w', nargs=4)   # internal: f0 f1 seg_path frames_dir|-
    o = a.parse_args()
    if o._w:
        f0, f1, seg, fd = o._w; worker(o.page, o.lang, int(f0), int(f1), seg, o.crf, o.preset, None if fd == '-' else fd); return
    # read duration/fps/SFX once
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome'); pg = b.new_page(viewport={'width': 1920, 'height': 1080}, screen={'width': 1920, 'height': 1080})
        pg.context.new_cdp_session(pg).send('Emulation.setDeviceMetricsOverride', {'width': 1920, 'height': 1080, 'deviceScaleFactor': 1,
                                            'mobile': False, 'screenWidth': 1920, 'screenHeight': 1080})   # same layout as workers
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('file://' + os.path.abspath(o.page) + f'?lang={o.lang}'); pg.wait_for_timeout(800)
        fps = pg.evaluate('window.FPS||30'); dur = pg.evaluate('window.DURATION||30')
        if errs: sys.exit('page error: ' + errs[0])
        with open(os.path.join(os.path.dirname(os.path.abspath(o.out)), f'sfx_{o.lang}.json'), 'w') as fh:
            json.dump(pg.evaluate('window.SFX||[]'), fh)
        b.close()
    N = int(round(fps * dur))
    if o.limit: N = min(N, o.limit)
    W = max(1, min(o.workers, N))
    if o.frames_dir: os.makedirs(o.frames_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='seg_'); bounds = [round(i * N / W) for i in range(W + 1)]
    t0 = time.time(); procs = []
    try:
        for i in range(W):
            seg = os.path.join(tmp, f'seg{i:02d}.mp4')
            procs.append((seg, subprocess.Popen([sys.executable, os.path.abspath(__file__), o.page, o.out, '--lang', o.lang,
                         '--crf', str(o.crf), '--preset', o.preset, '--_w', str(bounds[i]), str(bounds[i + 1]), seg, o.frames_dir or '-'])))
        # poll all workers instead of joining them in launch order: the first failure aborts the whole render at once
        live = list(procs)
        while live:
            for seg, pr in list(live):
                rc = pr.poll()
                if rc is None: continue
                live.remove((seg, pr))
                if rc != 0: sys.exit(f'segment {seg} failed (exit {rc}); stopping the other workers')
            time.sleep(0.2)
        lst = os.path.join(tmp, 'list.txt')
        with open(lst, 'w') as fh: fh.write(''.join(f"file '{s}'\n" for s, _ in procs))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', '-movflags', '+faststart', o.out], check=True)
    finally:
        for _, pr in procs:
            if pr.poll() is None: pr.kill()   # Ctrl-C / one failed worker → don't leave Chrome processes behind
        shutil.rmtree(tmp, ignore_errors=True)
    el = time.time() - t0
    print(f'rendered {N} frames with {W} workers in {el:.1f}s ({N / el:.1f} fps) -> {o.out}')

if __name__ == '__main__':
    main()
