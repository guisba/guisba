"""Offline, deterministic Chromium-to-MP4 film renderer.

Usage: python render.py [--fps 24] [--width 1280] [--samples-only]
Prerequisites: pip install -r requirements.txt; python -m playwright install chromium; ffmpeg
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess
from playwright.sync_api import sync_playwright
from score import compose, DURATION

ROOT = Path(__file__).resolve().parent

def run(fps: int, width: int, samples_only: bool):
    if width % 16:
        raise ValueError('Width must be divisible by 16')
    if not samples_only and not shutil.which('ffmpeg'):
        raise SystemExit('ffmpeg not found on PATH. Install FFmpeg to render MP4.')
    height=width*9//16
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, executable_path=shutil.which('chromium') or shutil.which('google-chrome') or None,
                                  args=['--disable-features=TranslateUI','--disable-web-security','--hide-scrollbars'])
        page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1, reduced_motion='reduce')
        page.set_content((ROOT/'index.html').read_text(encoding='utf-8'),wait_until='load')
        page.evaluate("document.body.classList.add('render')")
        frame_info=page.evaluate('window.__scenes')
        for sc in frame_info:
            print(f"Scene: {sc['name']} at {sc['start']:g}s, duration {sc['d']:g}s",flush=True)
        if samples_only:
            sampledir=ROOT/'samples';sampledir.mkdir(exist_ok=True)
            for sec in [1.9,7.8,14,21,27,32,37.1]:
                page.evaluate('t=>window.__frame(t)',sec)
                page.screenshot(path=str(sampledir/f'{sec:.1f}.png'),animations='disabled')
            print(f'Samples saved to {sampledir}')
            browser.close();return
        raw=ROOT/'video-only.mp4'
        cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-f','image2pipe','-framerate',str(fps),'-vcodec','png',
             '-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(raw)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        frames=round(DURATION*fps)
        try:
            for i in range(frames):
                page.evaluate('t=>window.__frame(t)',i/fps)
                frame=page.screenshot(type='png',animations='disabled')
                proc.stdin.write(frame)
                if i%max(1,fps*4)==0:
                    print(f'Render {i}/{frames} frames',flush=True)
        finally:
            proc.stdin.close()
            code=proc.wait()
            browser.close()
        if code:
            raise RuntimeError(f'ffmpeg video encoder returned {code}')
    audio=ROOT/'soundtrack.wav';compose(audio)
    final=ROOT/'guisba-portfolio-showcase.mp4'
    subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(raw),'-i',str(audio),
                    '-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-shortest',
                    '-movflags','+faststart',str(final)],check=True)
    raw.unlink()
    print(f'Completed: {final} ({final.stat().st_size/1024/1024:.1f} MiB)')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--fps',type=int,default=24)
    parser.add_argument('--width',type=int,default=1280)
    parser.add_argument('--samples-only',action='store_true')
    a=parser.parse_args();run(a.fps,a.width,a.samples_only)
