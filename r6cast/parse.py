"""Turn a Siege MatchReplay folder into events using r6-dissect.

r6-dissect (https://github.com/redraskal/r6-dissect) must be on PATH or set via R6DISSECT.
Times in the kill feed are the round clock counting down; we convert them to
seconds elapsed since the action phase began, which is what the director needs.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from .events import Event, Match

ROUND_SECONDS = 180  # ranked action phase


def run_dissect(replay_dir: Path) -> dict:
    exe = os.getenv("R6DISSECT", "r6-dissect")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "match.json"
        subprocess.run([exe, str(replay_dir), "-o", str(out)], check=True)
        return json.loads(out.read_text())


def to_match(d: dict, source: str) -> Match:
    rounds = d["rounds"]
    first = rounds[0]
    me = first["recordingPlayerID"]
    match = Match(source=source, duration=0)
    match.meta = {
        "map": first["map"]["name"],
        "mode": first["gamemode"]["name"],
        "type": first["matchType"]["name"],
        "recording_player": next((p["username"] for p in first["players"] if p["id"] == me), None),
        "teams": [t["name"] for t in first["teams"]],
        "stats": d.get("stats", []),
    }
    for r in rounds:
        n = r["roundNumber"] + 1
        players = {p["username"]: p for p in r["players"]}
        ours = r["teams"][1]
        match.events.append(Event(0, "round_start", round=n, note=json.dumps({
            "site": r.get("site"),
            "our_role": ours["role"],
            "lineup": {u: {"team": p["teamIndex"], "op": p["operator"]["name"]} for u, p in players.items()},
        })))
        last = 0.0
        for f in r.get("matchFeedback", []):
            t = float(ROUND_SECONDS - f.get("timeInSeconds", 0))
            last = max(last, t)
            kind = {"Kill": "kill", "DefuserPlantComplete": "plant",
                    "DefuserDisableComplete": "defuse"}.get(f["type"]["name"], f["type"]["name"].lower())
            match.events.append(Event(t, kind, round=n, killer=f.get("username"),
                                      victim=f.get("target"), headshot=bool(f.get("headshot"))))
        score = f'{ours["score"]}-{r["teams"][0]["score"]}'
        match.events.append(Event(last + 3, "round_end", round=n, score=score,
                                  note="won" if ours["won"] else "lost"))
    return match


def parse(replay_dir: Path) -> Match:
    return to_match(run_dissect(replay_dir), str(replay_dir))
