from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from dotenv import load_dotenv

load_dotenv()
app = typer.Typer(help="Turn R6 Siege recordings into broadcast videos with AI casters.")
LANG = os.getenv("CASTER_LANGUAGE", "en")


@app.command()
def calibrate(video: Path, at: float = 60.0, out: Path = Path("calibrate.png")):
    """Draw the OCR regions on a frame so you can check they line up."""
    from .detect import calibrate as _cal
    _cal(video, at, out)
    typer.echo(f"Wrote {out}")


@app.command()
def detect(video: Path, out: Path = Path("out/events.json")):
    from .detect import detect as _detect
    out.parent.mkdir(parents=True, exist_ok=True)
    m = _detect(video)
    m.save(out)
    typer.echo(f"{len(m.events)} events → {out}")


@app.command()
def commentate(events: Path = Path("out/events.json"), out: Path = Path("out/script.json")):
    from .commentary import write_script
    from .events import Match
    lines = write_script(Match.load(events), LANG)
    out.write_text(json.dumps(lines, indent=2, ensure_ascii=False))
    typer.echo(f"{len(lines)} lines → {out}")


@app.command()
def voice(script: Path = Path("out/script.json"), out: Path = Path("out/voice.json")):
    from .voice import render
    lines = render(json.loads(script.read_text()), out.parent / "audio", LANG)
    out.write_text(json.dumps(lines, indent=2, ensure_ascii=False))
    typer.echo(f"Rendered {len(lines)} lines")


@app.command()
def edit(video: Path, voice_json: Path = Path("out/voice.json"), out: Path = Path("out/broadcast.mp4")):
    from .edit import mix
    mix(video, json.loads(voice_json.read_text()), out)
    typer.echo(f"Broadcast → {out}")


@app.command()
def run(video: Path, out: Path = Path("out")):
    """Run every stage end to end."""
    out.mkdir(parents=True, exist_ok=True)
    detect(video, out / "events.json")
    commentate(out / "events.json", out / "script.json")
    voice(out / "script.json", out / "voice.json")
    edit(video, out / "voice.json", out / "broadcast.mp4")


if __name__ == "__main__":
    app()
