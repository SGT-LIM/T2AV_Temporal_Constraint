#!/usr/bin/env python3
"""Waveform + frame panel for one clip window (pipeline v4 step 4 observation set, 10/28). No API calls.

One PNG, 1550 px wide (up to 1800 px when frames would be narrower than 150 px):
  top    = mono audio waveform of [t1 - pad, t2 + pad], clamped to the clip; x ticks at whole seconds; no other marks or text
  bottom = frames sampled evenly across the same span, each centred under its time on the same x axis, its exact time
           written under it
Frame density (10/28 rev 3), span = shown span:
  span <= 10 s: one frame per 0.5 s, at most 16 (spacing span / 16 when the span is 8-10 s); one row if <= 8 frames,
                else two interleaved rows (frame k in row k % 2), so every frame stays under its own time
  span  > 10 s: one frame per 2 s (round(span / 2)); one row if frames are >= 150 px wide, else two interleaved rows
  Width: 1550 px; widened up to 1800 px if a frame would be < 150 px; frames are capped at 400 px.

panel_peak (10/28 rev 4): onsets from the window's audio ONLY: local maxima of librosa onset_strength (normalised height
  >= 0.10, prominence >= 0.07), strongest first with >= 0.3 s separation, top 6, shown in time order. Each peak -> two frames side by side (peak - 0.5 s, peak), labelled with their
  times; pairs laid out left to right in time order (one row if <= 3 pairs, else two rows of <= 3 pairs). Each peak is a
  thin vertical line on the waveform; nothing else is drawn. < 2 peaks -> panel_even, recorded as fallback.

  python gepa_stage2/render_panel.py VIDEO T1 T2 OUT.png [--pad 2] [--mode even|peak]
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "4"                  # SCC job has 4 cores (10/28: a run was killed at 5.4 cores); set before numpy/librosa import
FF_THREADS = ["-threads", "2"]            # every ffmpeg call: 2 threads for decode and encode
import argparse, io, math, subprocess
import numpy as np

SR = 16000
DPI = 100
W_MIN_PX, W_MAX_PX = 1550, 1800
MIN_FRAME_PX, MAX_FRAME_PX = 150, 400
LEFT, RIGHT = 0.03, 0.99
FILL = 0.94                       # frame width / slot width within a row


def probe_duration(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def audio_span(video, a, b):
    r = subprocess.run(["ffmpeg", "-v", "error", *FF_THREADS, "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(video), *FF_THREADS, "-vn", "-ac", "1",
                        "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32)


def frame_at(video, t, width=360):
    from PIL import Image
    r = subprocess.run(["ffmpeg", "-v", "error", *FF_THREADS, "-ss", f"{t:.3f}", "-i", str(video), *FF_THREADS, "-frames:v", "1", "-vf", f"scale={width}:-2",
                        "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True)
    return np.asarray(Image.open(io.BytesIO(r.stdout)).convert("RGB"))


def window(video, t1, t2, pad):
    dur = probe_duration(video)
    return max(0.0, t1 - pad), min(dur, t2 + pad), dur


def axis_px(w, fpx):
    """axis width in px at figure width w, leaving half a frame + 10 px each side for frames centred at the edges."""
    return w - 2 * max(w * LEFT, fpx / 2 + 10)


def layout(span):
    """-> n_frames, rows, width_px, frame_px (display width of one frame)."""
    if span <= 10.0:
        n = max(2, min(16, int(round(span / 0.5))))
        rows_opts = [1] if n <= 8 else [2]
    else:
        n = max(2, int(round(span / 2.0)))
        rows_opts = [1, 2]
    step = span / n
    for rows in rows_opts:
        for w in range(W_MIN_PX, W_MAX_PX + 1, 10):
            k = rows * step / span * FILL
            fpx = min(k * (w - 20) / (1 + k), MAX_FRAME_PX)        # solves fpx = k * axis_px(w, fpx) when the margin binds
            fpx = min(fpx, k * axis_px(w, fpx))
            if fpx >= MIN_FRAME_PX:
                return n, rows, w, fpx
    rows = rows_opts[-1]
    k = rows * step / span * FILL
    fpx = k * (W_MAX_PX - 20) / (1 + k)
    return n, rows, W_MAX_PX, min(fpx, k * axis_px(W_MAX_PX, fpx))     # < 150 px: recorded by the caller


def render(video, t1, t2, out, pad=2.0, n_frames=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    a, b, _ = window(video, t1, t2, pad)
    span = b - a
    n, rows, wpx, fpx = layout(span)
    if n_frames:
        n = n_frames
    step = span / n
    times = [a + (i + 0.5) * step for i in range(n)]
    frames = [frame_at(video, ti, width=int(max(360, math.ceil(fpx / 2) * 2))) for ti in times]
    fh, fw = frames[0].shape[:2]
    W_in = wpx / DPI
    ax_w_in = axis_px(wpx, fpx) / DPI
    lm = (wpx - axis_px(wpx, fpx)) / 2 / wpx               # left margin as a figure fraction (symmetric)
    img_w_in = fpx / DPI
    img_h_in = img_w_in * fh / fw
    lab_in, row_gap_in = 0.22, 0.08
    frames_h_in = rows * (img_h_in + lab_in) + (rows - 1) * row_gap_in
    wave_h_in, gap_in, bottom_in, top_in = 1.9, 0.45, 0.05, 0.12
    H = bottom_in + frames_h_in + gap_in + wave_h_in + top_in
    fig = plt.figure(figsize=(W_in, H), dpi=DPI)
    ax_w = fig.add_axes([lm, (bottom_in + frames_h_in + gap_in) / H, 1 - 2 * lm, wave_h_in / H])
    ax_f = fig.add_axes([lm, bottom_in / H, 1 - 2 * lm, frames_h_in / H])
    waveform(ax_w, audio_span(video, a, b), a, b, int(ax_w_in * DPI))
    # frames: y axis in inches so the frame aspect ratio is kept; row 0 on top
    w_sec = img_w_in / ax_w_in * span
    for i, (ti, im) in enumerate(zip(times, frames)):
        r = i % rows
        y0 = frames_h_in - (r + 1) * img_h_in - r * (lab_in + row_gap_in)
        h_ = ax_f.imshow(im, extent=[ti - w_sec / 2, ti + w_sec / 2, y0, y0 + img_h_in], aspect="auto", interpolation="bilinear")
        h_.set_clip_on(False)                                 # edge frames may overhang the axis into the reserved margin
        ax_f.text(ti, y0 - 0.03, f"{ti:.2f}", ha="center", va="top", fontsize=8, clip_on=False)
    ax_f.set_xlim(a, b)
    ax_f.set_ylim(0, frames_h_in)
    ax_f.axis("off")
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return dict(mode="panel_even", span=[round(a, 3), round(b, 3)], frame_times=[round(x, 3) for x in times], n_frames=n, frame_rows=rows,
                width_px=wpx, frame_px=round(fpx, 1), frame_px_ok=bool(fpx >= MIN_FRAME_PX - 0.5))


PEAK_SEP, PEAK_TOP, PEAK_PRE = 0.3, 6, 0.5


PEAK_MIN_REL, PEAK_PROM = 0.10, 0.07     # on the max-normalised onset envelope (0.07 = librosa onset_detect default delta)


def detect_peaks(y, sr=SR):
    """onset peaks of the audio only: [(time from window start, strength)], sorted by time.
    Local maxima of librosa onset_strength with normalised height >= 0.10 and prominence >= 0.07, then greedy by strength
    (strongest first), dropping any peak within 0.3 s of an already kept one, up to 6. (librosa onset_detect applies its
    wait in time order, so a weak early onset can block a stronger one 0.3 s later; this keeps the strongest instead.)"""
    import librosa
    from scipy.signal import find_peaks
    hop = 512
    env = librosa.onset.onset_strength(y=y.astype(np.float32), sr=sr, hop_length=hop)
    if not len(env) or env.max() <= 0:
        return []
    en = env / env.max()
    idx, _ = find_peaks(en, height=PEAK_MIN_REL, prominence=PEAK_PROM)
    keep = []
    for f in sorted(idx, key=lambda f: -env[f]):
        t = f * hop / sr
        if all(abs(t - k[0]) >= PEAK_SEP for k in keep):
            keep.append((float(t), float(env[f])))
        if len(keep) == PEAK_TOP:
            break
    return sorted(keep)


def waveform(ax, y, a, b, cols):
    t = a + np.arange(len(y)) / SR
    if len(y) > 2 * cols:
        k = len(y) // cols
        yy = y[: k * cols].reshape(cols, k)
        ax.fill_between(t[: k * cols].reshape(cols, k).mean(1), yy.min(1), yy.max(1), color="#333333", linewidth=0)
    else:
        ax.plot(t, y, color="#333333", linewidth=0.6)
    lim = max(1e-4, float(np.abs(y).max()) * 1.05) if len(y) else 1.0
    ax.set_ylim(-lim, lim)
    ax.set_yticks([])
    ax.set_xlim(a, b)
    ticks = np.arange(math.ceil(a), math.floor(b) + 1, 1.0)
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{int(x)}" for x in ticks], fontsize=9)
    for s_ in ("top", "right", "left"):
        ax.spines[s_].set_visible(False)


def render_peak(video, t1, t2, out, pad=2.0):
    a, b, dur = window(video, t1, t2, pad)
    y = audio_span(video, a, b)
    pk = detect_peaks(y)
    if len(pk) < 2:
        r = render(video, t1, t2, out, pad)
        r.update(mode="panel_peak", fallback="panel_even", n_peaks=len(pk), peaks=[[round(a + t, 3), round(s, 3)] for t, s in pk])
        return r
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    peaks = [a + t for t, _ in pk]
    pairs = [(max(0.0, p - PEAK_PRE), p) for p in peaks]
    per_row = 3
    rows = 1 if len(pairs) <= per_row else 2
    cols_pairs = min(per_row, len(pairs))
    wpx = W_MIN_PX
    W_in = wpx / DPI
    ax_w_in = W_in * (RIGHT - LEFT)
    pair_gap_in, in_gap_in = 0.35, 0.04
    img_w_in = (ax_w_in - (cols_pairs - 1) * pair_gap_in - cols_pairs * in_gap_in) / (2 * cols_pairs)
    img_w_in = min(img_w_in, MAX_FRAME_PX / DPI)
    frames = [[frame_at(video, t, width=int(max(360, img_w_in * DPI))) for t in pr] for pr in pairs]
    fh, fw = frames[0][0].shape[:2]
    img_h_in = img_w_in * fh / fw
    lab_in, row_gap_in = 0.22, 0.12
    frames_h_in = rows * (img_h_in + lab_in) + (rows - 1) * row_gap_in
    wave_h_in, gap_in, bottom_in, top_in = 1.9, 0.45, 0.05, 0.12
    H = bottom_in + frames_h_in + gap_in + wave_h_in + top_in
    fig = plt.figure(figsize=(W_in, H), dpi=DPI)
    ax_w = fig.add_axes([LEFT, (bottom_in + frames_h_in + gap_in) / H, RIGHT - LEFT, wave_h_in / H])
    ax_f = fig.add_axes([LEFT, bottom_in / H, RIGHT - LEFT, frames_h_in / H])
    waveform(ax_w, y, a, b, int(ax_w_in * DPI))
    for p in peaks:
        ax_w.axvline(p, color="#c0392b", linewidth=0.8)
    pair_w = 2 * img_w_in + in_gap_in
    row_w = cols_pairs * pair_w + (cols_pairs - 1) * pair_gap_in
    x0 = (ax_w_in - row_w) / 2
    for i, (pr, ims) in enumerate(zip(pairs, frames)):
        r, c = divmod(i, per_row)
        y0 = frames_h_in - (r + 1) * img_h_in - r * (lab_in + row_gap_in)
        for j, (t, im) in enumerate(zip(pr, ims)):
            xl = x0 + c * (pair_w + pair_gap_in) + j * (img_w_in + in_gap_in)
            ax_f.imshow(im, extent=[xl, xl + img_w_in, y0, y0 + img_h_in], aspect="auto", interpolation="bilinear")
            ax_f.text(xl + img_w_in / 2, y0 - 0.03, f"{t:.2f}", ha="center", va="top", fontsize=8)
    ax_f.set_xlim(0, ax_w_in)
    ax_f.set_ylim(0, frames_h_in)
    ax_f.axis("off")
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return dict(mode="panel_peak", fallback=None, span=[round(a, 3), round(b, 3)], n_peaks=len(pk),
                peaks=[[round(a + t, 3), round(s, 3)] for t, s in pk], frame_times=[[round(x, 3) for x in pr] for pr in pairs],
                n_frames=2 * len(pairs), frame_rows=rows, width_px=wpx, frame_px=round(img_w_in * DPI, 1),
                frame_px_ok=bool(img_w_in * DPI >= MIN_FRAME_PX - 0.5))


def describe(video, t1, t2, pad=2.0, mode="even"):
    """Render details of a panel WITHOUT drawing it (same deterministic rules as render / render_peak); used to fill the
    manifest for panels that already exist on disk."""
    a, b, _ = window(video, t1, t2, pad)
    span = b - a
    if mode == "peak":
        pk = detect_peaks(audio_span(video, a, b))
        if len(pk) >= 2:
            peaks = [a + t for t, _ in pk]
            img_w_in = min((W_MIN_PX / DPI * (RIGHT - LEFT) - (min(3, len(pk)) - 1) * 0.35 - min(3, len(pk)) * 0.04) / (2 * min(3, len(pk))),
                           MAX_FRAME_PX / DPI)
            return dict(mode="panel_peak", fallback=None, span=[round(a, 3), round(b, 3)], n_peaks=len(pk),
                        peaks=[[round(a + t, 3), round(s_, 3)] for t, s_ in pk],
                        frame_times=[[round(max(0.0, p - PEAK_PRE), 3), round(p, 3)] for p in peaks], n_frames=2 * len(pk),
                        frame_rows=1 if len(pk) <= 3 else 2, width_px=W_MIN_PX, frame_px=round(img_w_in * DPI, 1),
                        frame_px_ok=bool(img_w_in * DPI >= MIN_FRAME_PX - 0.5))
        fb = dict(mode="panel_peak", fallback="panel_even", n_peaks=len(pk), peaks=[[round(a + t, 3), round(s_, 3)] for t, s_ in pk])
    else:
        fb = dict(mode="panel_even")
    n, rows, wpx, fpx = layout(span)
    step = span / n
    return {**dict(span=[round(a, 3), round(b, 3)], frame_times=[round(a + (i + 0.5) * step, 3) for i in range(n)], n_frames=n,
                   frame_rows=rows, width_px=wpx, frame_px=round(fpx, 1), frame_px_ok=bool(fpx >= MIN_FRAME_PX - 0.5)), **fb}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("t1", type=float); ap.add_argument("t2", type=float); ap.add_argument("out")
    ap.add_argument("--pad", type=float, default=2.0)
    ap.add_argument("--mode", choices=["even", "peak"], default="even")
    a = ap.parse_args()
    print((render_peak if a.mode == "peak" else render)(a.video, a.t1, a.t2, a.out, a.pad))
