"""Mix caster audio over the game and render the broadcast with ffmpeg."""
from __future__ import annotations

import subprocess
from pathlib import Path

GAME_VOL = 0.35      # game audio level while casters talk (sidechain ducked)


def mix(video: Path, lines: list[dict], out: Path) -> None:
    """Place each caster clip at its timestamp, duck game audio under it."""
    inputs = ["-i", str(video)]
    delays = []
    for i, line in enumerate(lines):
        inputs += ["-i", line["file"]]
        ms = int(line["t"] * 1000)
        delays.append(f"[{i + 1}:a]adelay={ms}|{ms},aformat=channel_layouts=stereo[c{i}]")

    n = len(lines)
    casters = "".join(f"[c{i}]" for i in range(n))
    graph = ";".join(delays) + (
        f";{casters}amix=inputs={n}:normalize=0[voice]"
        f";[voice]asplit[v1][v2]"
        f";[0:a]volume={GAME_VOL}[gq]"
        f";[gq][v1]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400[game]"
        f";[game][v2]amix=inputs=2:normalize=0[aout]"
    )
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", graph,
           "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out)]
    subprocess.run(cmd, check=True)
