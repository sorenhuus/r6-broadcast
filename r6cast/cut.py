"""Assemble the broadcast from captured passes using the shot list.

Each pass recording is synced to the round clock by OCR on the HUD timer.
That gives a video-time → round-time map per file, so a shot (round time
start..end) can be cut from any pass frame-accurately.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import cv2

from .detect import TIMER, crop, ocr

ROUND_SECONDS = 180
OUT_W, OUT_H = 1920, 1080


def clock_offset(video: Path, probe_every: float = 1.0, max_probe: float = 90) -> float:
    """Return video_time at which round_time == 0 (action phase start)."""
    cap = cv2.VideoCapture(str(video))
    samples = []
    t = 0.0
    while t < max_probe and len(samples) < 8:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        m = re.search(r"(\d):(\d\d)", ocr(crop(frame, TIMER)))
        if m:
            remaining = int(m[1]) * 60 + int(m[2])
            if remaining <= ROUND_SECONDS:
                samples.append(t - (ROUND_SECONDS - remaining))
        t += probe_every
    cap.release()
    if not samples:
        raise RuntimeError(f"Could not read the round timer in {video}")
    samples.sort()
    return samples[len(samples) // 2]


def _frame_filter(src_w: int, src_h: int) -> str:
    # 32:9 (3840x1080) → centre crop to 16:9
    if src_w / src_h > 16 / 9 + 0.01:
        cw = int(src_h * 16 / 9)
        return f"crop={cw}:{src_h}:{(src_w - cw) // 2}:0,scale={OUT_W}:{OUT_H}"
    return f"scale={OUT_W}:{OUT_H}"


def cut(shots_path: Path, passes_path: Path, out_dir: Path) -> list[Path]:
    shots = json.loads(shots_path.read_text())["shots"]
    passes = {(p["round"], p["player"], p["view"]): Path(p["file"]) for p in json.loads(passes_path.read_text())}
    offsets: dict[Path, float] = {}
    out_dir.mkdir(parents=True, exist_ok=True)
    clips = []
    for i, s in enumerate(shots):
        src = passes[(s["round"], s["player"], s["view"])]
        if src not in offsets:
            offsets[src] = clock_offset(src)
        cap = cv2.VideoCapture(str(src))
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        vf = _frame_filter(w, h)
        af = "anull"
        if s.get("slowmo"):
            vf += ",setpts=2.0*PTS"
            af = "atempo=0.5"
        start = offsets[src] + s["start"]
        clip = out_dir / f"shot_{i:03d}.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{s['end'] - s['start']:.3f}", "-i", str(src),
            "-vf", vf + ",fps=60", "-af", af, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-c:a", "aac", "-ar", "48000", str(clip)], check=True)
        clips.append(clip)
    concat = out_dir / "concat.txt"
    concat.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    final = out_dir / "program.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(final)], check=True)
    return clips
