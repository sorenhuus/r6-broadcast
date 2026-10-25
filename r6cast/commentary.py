"""Generate two-caster commentary from detected events with Claude."""
from __future__ import annotations

import json
import os
from dataclasses import asdict

import anthropic

from .events import Match

MODEL = os.getenv("R6CAST_MODEL", "claude-sonnet-5-5")

SYSTEM = """You are writing the script for a Rainbow Six Siege esports broadcast.
Two casters:
- PBP (play-by-play): fast, energetic, calls the action as it happens.
- ANALYST (colour): calmer, explains strategy, utility, round economy, clutch context.

Rules:
- Every line is anchored to a timestamp (seconds) from the event list.
- Keep lines short enough to speak in the gap before the next event (~2.5 words/sec).
- Hype multi-kills, clutches, and round-deciding kills. Stay quiet-ish in slow moments.
- Never invent kills or players that are not in the events.
- Language: {lang}.

Return ONLY JSON: {{"lines": [{{"t": float, "speaker": "PBP"|"ANALYST", "text": str}}]}}"""


def write_script(match: Match, lang: str = "en") -> list[dict]:
    client = anthropic.Anthropic()
    events = [asdict(e) for e in match.events]
    msg = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM.format(lang="Danish" if lang == "da" else "English"),
        messages=[{
            "role": "user",
            "content": f"Match duration: {match.duration:.0f}s\nEvents:\n{json.dumps(events, indent=1)}",
        }],
    )
    text = msg.content[0].text
    start, end = text.find("{"), text.rfind("}") + 1
    return json.loads(text[start:end])["lines"]
