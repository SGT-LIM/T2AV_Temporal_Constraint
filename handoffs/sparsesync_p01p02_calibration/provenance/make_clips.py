#!/usr/bin/env python3
"""Cut real clips for items and apply media ops (cut / cut+mute / cut+audio_shift).

  python make_clips.py items_hdepic_medium.json --videos ../real_av/hdepic/videos --out ../real_av/hdepic/clips
  python make_clips.py items_countixav_val.json --videos ../real_av/countixav/videos --out ../real_av/countixav/clips

Variants that share the same (video, clip, media op) share one file: e.g. original, absent-sound, hand/noun swap
and order swap all point to the plain cut. Writes <items>_with_clips.json with `clip_path` filled in.
Needs `module load ffmpeg/8.1`. Resumable: existing output files are skipped.
"""
import argparse, json, subprocess, sys
from pathlib import Path

def run(cmd):
    r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if r.returncode: print('  ffmpeg error:', r.stderr.strip().splitlines()[-1][:200])
    return r.returncode == 0

def make(src, dst, lo, hi, op, shift=0.0):
    dur = hi - lo
    base = ['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{lo:.3f}', '-t', f'{dur:.3f}', '-i', str(src)]
    venc = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p']
    if op == 'cut':
        return run(base + venc + ['-c:a', 'aac', '-b:a', '128k', str(dst)])
    if op == 'cut+mute':
        return run(base + venc + ['-an', str(dst)])
    if op == 'cut+audio_shift':
        # shift>0: audio LATE by `shift` s (sound after its action); shift<0: audio EARLY.
        # Implemented by reading the same file twice with different start offsets (no filter timestamp tricks,
        # robust across ffmpeg versions). Audio source start = lo - shift; if that is < 0 pad with silence.
        a_start = lo - shift
        pad_ms = int(round(max(0.0, -a_start) * 1000))
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{lo:.3f}', '-t', f'{dur:.3f}', '-i', str(src),
               '-ss', f'{max(0.0, a_start):.3f}', '-t', f'{dur:.3f}', '-i', str(src), '-map', '0:v:0', '-map', '1:a:0']
        af = (f'adelay={pad_ms}|{pad_ms},' if pad_ms else '') + f'apad,atrim=0:{dur:.3f}'
        return run(cmd + venc + ['-af', af, '-c:a', 'aac', '-b:a', '128k', str(dst)])
    raise ValueError(op)

def first_sound(path, thresh='-35dB'):
    """Time (s) of the first non-silent audio, via silencedetect. None if no audio."""
    r = subprocess.run(['ffmpeg', '-i', str(path), '-af', f'silencedetect=n={thresh}:d=0.05', '-f', 'null', '-'],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True).stderr
    ends = [float(l.split('silence_end:')[1].split('|')[0]) for l in r.splitlines() if 'silence_end' in l]
    if 'Audio:' not in r: return None
    return ends[0] if ends else 0.0

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('items'); ap.add_argument('--videos', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--limit', type=int, default=0, help='only first N items (smoke test)')
    ap.add_argument('--verify', action='store_true', help='after cutting, compare first-sound time of orig vs shifted clips')
    a = ap.parse_args()
    items = json.load(open(a.items)); V = Path(a.videos); O = Path(a.out); O.mkdir(parents=True, exist_ok=True)
    if a.limit: items = items[:a.limit]
    done, missing, fail = {}, set(), 0
    for it in items:
        lo, hi = it['clip']; op = it['media']['op']; shift = it['media'].get('shift_s', 0.0)
        key = (it['video_id'], round(lo, 2), round(hi, 2), op, shift)
        if key not in done:
            src = V / f"{it['video_id']}.mp4"
            if not src.exists():
                missing.add(it['video_id']); done[key] = None
            else:
                tag = {'cut': 'orig', 'cut+mute': 'mute', 'cut+audio_shift': f'shift{int(shift*1000):+d}ms'}[op]
                dst = O / f"{it['video_id']}_{int(lo*100):07d}_{tag}.mp4"
                if not dst.exists():
                    ok = make(src, dst, lo, hi, op, shift)
                    if not ok: fail += 1; dst = None
                done[key] = str(dst) if dst else None
                print(f"  {len(done):4d} {dst.name if dst else 'FAIL'}")
        it['clip_path'] = done[key]
    out = Path(a.items).with_name(Path(a.items).stem + '_with_clips.json')
    json.dump(items, open(out, 'w'), indent=1)
    n_ok = sum(1 for it in items if it['clip_path'])
    print(f"\n{n_ok}/{len(items)} items have clips; {len(done)} unique media files; {fail} ffmpeg failures; "
          f"{len(missing)} source videos missing{(': ' + ', '.join(sorted(missing)[:5])) if missing else ''}")
    print(f"-> {out}")
    if a.verify:
        print("\nverify (first non-silent second): orig vs shifted")
        origs = {k[:3]: v for k, v in done.items() if k[3] == 'cut' and v}
        for k, v in done.items():
            if k[3] == 'cut+audio_shift' and v and k[:3] in origs:
                fo, fs = first_sound(origs[k[:3]]), first_sound(v)
                print(f"  {Path(v).name}: orig first sound {fo}s, shifted {fs}s, expected shift {k[4]:+.1f}s")
