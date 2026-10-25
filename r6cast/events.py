"""Shared event model passed between pipeline stages."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Event:
    t: float                 # seconds into the recording
    kind: str                # kill | round_start | round_end | plant | defuse
    round: int | None = None
    killer: str | None = None
    victim: str | None = None
    headshot: bool = False
    score: str | None = None  # e.g. "3-2"
    note: str | None = None


@dataclass
class Match:
    source: str
    duration: float
    events: list[Event] = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: Path) -> "Match":
        d = json.loads(path.read_text())
        return cls(d["source"], d["duration"], [Event(**e) for e in d["events"]])
