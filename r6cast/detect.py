"""Find match events by OCR on the kill feed and round timer.

Screen regions are fractions of the frame (x, y, w, h) at 16:9 and need
calibrating against a real recording — see `r6cast calibrate`.
"""
from __future__ import annotations

import re
from pathlib import Path

import cv2
import pytesseract

from .events import Event, Match

KILLFEED = (0.70, 0.08, 0.29, 0.22)   # top-right
TIMER = (0.465, 0.015, 0.07, 0.045)   # top-centre
SAMPLE_FPS = 2


def crop(frame, region):
    h, w = frame.shape[:2]
    x, y, rw, rh = region
    return frame[int(y * h): int((y + rh) * h), int(x * w): int((x + rw) * w)]


def ocr(img) -> str:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return pytesseract.image_to_string(bw, config="--psm 6")


def parse_killfeed(text: str) -> list[tuple[str, str]]:
    """Kill feed lines look like 'Killer  [icon]  Victim'. Icons OCR as noise,
    so keep the first and last name-like tokens on each line."""
    pairs = []
    for line in text.splitlines():
        names = re.findall(r"[A-Za-z0-9_.\-]{3,}", line)
        if len(names) >= 2:
            pairs.append((names[0], names[-1]))
    return pairs


def detect(video: Path) -> Match:
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 60
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    step = max(1, int(fps / SAMPLE_FPS))

    match = Match(source=str(video), duration=total / fps)
    seen: set[tuple[str, str]] = set()
    timer_visible = False
    rnd = 0
    i = 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % step == 0:
            _, frame = cap.retrieve()
            t = i / fps

            # Round boundaries: timer appears/disappears.
            has_timer = bool(re.search(r"\d:\d\d", ocr(crop(frame, TIMER))))
            if has_timer and not timer_visible:
                rnd += 1
                seen.clear()
                match.events.append(Event(t, "round_start", round=rnd))
            elif not has_timer and timer_visible:
                match.events.append(Event(t, "round_end", round=rnd))
            timer_visible = has_timer

            for killer, victim in parse_killfeed(ocr(crop(frame, KILLFEED))):
                if (killer, victim) not in seen:
                    seen.add((killer, victim))
                    match.events.append(Event(t, "kill", round=rnd, killer=killer, victim=victim))
        i += 1
    cap.release()
    return match


def calibrate(video: Path, at: float, out: Path) -> None:
    """Save a frame with the OCR regions drawn on it, for tuning coordinates."""
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_MSEC, at * 1000)
    ok, frame = cap.read()
    if not ok:
        raise SystemExit(f"Could not read frame at {at}s")
    h, w = frame.shape[:2]
    for region, colour in ((KILLFEED, (0, 255, 0)), (TIMER, (0, 0, 255))):
        x, y, rw, rh = region
        cv2.rectangle(frame, (int(x * w), int(y * h)), (int((x + rw) * w), int((y + rh) * h)), colour, 3)
    cv2.imwrite(str(out), frame)
