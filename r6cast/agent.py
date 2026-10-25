"""Capture agent for the replay VM. Run elevated: `python -m r6cast.agent C:\\r6cast`.

Watches <root>/jobs for JSON job files, carries each one out in the Siege replay
viewer while OBS records, and writes the result to <root>/done.

Job file:
  {"id": "R03_hrhuus_third", "round": 3, "slot": 6, "view": "third",
   "seconds": 205, "config": "C:/r6cast/capture.toml"}

Special job: {"id": "...", "action": "screenshot"} saves a full-screen PNG
to done/, for checking what the viewer is showing.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

from .capture import OBS, Viewer, _load_cfg


def screenshot(path: Path) -> None:
    from PIL import ImageGrab
    ImageGrab.grab(all_screens=True).save(path)


def run_job(job: dict, root: Path) -> dict:
    if job.get("action") == "screenshot":
        out = root / "done" / f"{job['id']}.png"
        screenshot(out)
        return {"ok": True, "file": str(out)}

    cfg = _load_cfg(Path(job.get("config", root / "capture.toml")))
    viewer, obs = Viewer(cfg), OBS(cfg.get("obs", {}))
    viewer.run("open_round", round=job["round"])
    viewer.select(job["slot"], job.get("view", "pov"))
    obs.start(job["id"])
    viewer.run("play")
    time.sleep(job.get("seconds", cfg.get("round_seconds", 205)))
    path = obs.stop()
    viewer.run("exit_round")
    screenshot(root / "done" / f"{job['id']}.png")
    return {"ok": True, "file": path}


def main(root: str) -> None:
    root_p = Path(root)
    jobs, done = root_p / "jobs", root_p / "done"
    jobs.mkdir(parents=True, exist_ok=True)
    done.mkdir(parents=True, exist_ok=True)
    print(f"r6cast agent watching {jobs}")
    while True:
        for f in sorted(jobs.glob("*.json")):
            job = json.loads(f.read_text())
            print("job", job.get("id"))
            try:
                result = run_job(job, root_p)
            except Exception:
                result = {"ok": False, "error": traceback.format_exc()}
            (done / f.name).write_text(json.dumps({**job, **result}, indent=2))
            f.unlink()
        time.sleep(2)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else r"C:\r6cast")
