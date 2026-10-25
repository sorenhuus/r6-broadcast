"""Multipass capture on the Windows PC running Siege.

For each pass (round, player, view) from shots.json:
  1. open that round in the replay viewer
  2. select the player and camera view
  3. start OBS recording, play the round, stop recording

Keys and click positions live in capture.toml (filled in by calibration),
because the replay viewer has no public API.

Needs: OBS 28+ with WebSocket server enabled, `pip install obsws-python pydirectinput`.
"""
from __future__ import annotations

import json
import time
import tomllib
from pathlib import Path

ROUND_PLAY_SECONDS = 200  # action phase + buffer; overridden per round from events


def _load_cfg(path: Path) -> dict:
    return tomllib.loads(path.read_text())


class Viewer:
    """Drives the Siege replay viewer with keyboard/mouse input."""

    def __init__(self, cfg: dict):
        import pydirectinput  # Windows only
        self.inp = pydirectinput
        self.cfg = cfg

    def _do(self, step):
        kind, arg = step[0], step[1:]
        if kind == "key":
            n = int(arg[1]) if len(arg) > 1 else 1
            if n > 0:
                self.inp.press(arg[0], presses=n, interval=0.15)
        elif kind == "click":
            self.inp.click(int(arg[0]), int(arg[1]))
        elif kind == "wait":
            time.sleep(float(arg[0]))

    def run(self, name: str, **fmt):
        for step in self.cfg["sequences"][name]:
            self._do([s.format(**fmt) if isinstance(s, str) else s for s in step])

    def select(self, slot: int, view: str):
        self.run("select_player", slot=slot, steps=slot - 1)
        if view == "third":
            self.run("third_person")


class OBS:
    def __init__(self, cfg: dict):
        import obsws_python as obs
        self.c = obs.ReqClient(host=cfg.get("host", "localhost"), port=cfg.get("port", 4455),
                               password=cfg.get("password", ""))

    def start(self, name: str):
        self.c.set_profile_parameter("Output", "FilenameFormatting", name)
        self.c.start_record()

    def stop(self) -> str:
        return self.c.stop_record().output_path


def player_slots(events_path: Path) -> dict[int, dict[str, int]]:
    """Viewer cards: team index 0 on the left, team 1 on the right, each in reverse
    r6-dissect lineup order. Slots run 1-10 left to right."""
    match = json.loads(events_path.read_text())
    slots = {}
    for e in match["events"]:
        if e["kind"] == "round_start":
            lineup = json.loads(e["note"])["lineup"]
            left = [u for u, v in lineup.items() if v["team"] == 0][::-1]
            right = [u for u, v in lineup.items() if v["team"] == 1][::-1]
            slots[e["round"]] = {u: i + 1 for i, u in enumerate(left + right)}
    return slots


def capture(shots_path: Path, events_path: Path, cfg_path: Path, out_dir: Path, only_round: int | None = None):
    cfg = _load_cfg(cfg_path)
    plan = json.loads(shots_path.read_text())["passes"]
    slots = player_slots(events_path)
    viewer, obs = Viewer(cfg), OBS(cfg.get("obs", {}))
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "passes.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    done = {(m["round"], m["player"], m["view"]) for m in manifest}

    for p in plan:
        key = (p["round"], p["player"], p["view"])
        if key in done or (only_round and p["round"] != only_round):
            continue
        name = f"R{p['round']:02d}_{p['player']}_{p['view']}".replace(".", "_")
        print("Capturing", name)
        viewer.run("open_round", round=p["round"])
        viewer.select(slots[p["round"]][p["player"]], p["view"])
        obs.start(name)
        viewer.run("play")
        time.sleep(cfg.get("round_seconds", ROUND_PLAY_SECONDS))
        path = obs.stop()
        viewer.run("exit_round")
        manifest.append({**p, "file": path})
        manifest_path.write_text(json.dumps(manifest, indent=2))  # resumable
