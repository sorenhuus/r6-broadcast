"""Choose camera shots for each round from match events.

Times are seconds since the action phase began (round clock 3:00 = 0s).
Output shots tell the capture stage which (player, view) passes to record,
and tell the cut stage which pass to use for each slice of time.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .events import Match

LEAD = 5.0          # seconds on the killer before the kill
TAIL = 1.5          # seconds held after the kill
MAX_GAP = 12.0      # quiet stretches longer than this are cut from the broadcast
MIN_SHOT = 3.0
MULTI_WINDOW = 10.0  # kills by one player within this window = multi-kill


@dataclass
class Shot:
    round: int
    start: float
    end: float
    player: str
    view: str = "pov"          # pov | third
    tag: str = ""              # kill | clutch | plant | multikill-replay | establish
    slowmo: bool = False
    at: float | None = None    # time of the key moment in this shot


def _round_events(match: Match, rnd: int):
    evs = [e for e in match.events if e.round == rnd]
    start = next(e for e in evs if e.kind == "round_start")
    info = json.loads(start.note)
    action = sorted((e for e in evs if e.kind in ("kill", "plant", "defuse")), key=lambda e: e.t)
    # Kills logged at 0:00 during the defuser phase come out as t=180; spread them after the previous event.
    prev = 0.0
    for e in action:
        if e.t >= 180:
            e.t = prev + 4
        prev = e.t
    return info, sorted(action, key=lambda e: e.t)


def direct_round(match: Match, rnd: int) -> list[Shot]:
    info, action = _round_events(match, rnd)
    lineup = info["lineup"]
    alive = {u: True for u in lineup}
    team = {u: v["team"] for u, v in lineup.items()}
    shots: list[Shot] = []
    clutching: set[str] = set()

    # Establishing shot on the recording player.
    me = match.meta.get("recording_player") or next(iter(lineup))
    shots.append(Shot(rnd, 0, 6, me, "third", "establish"))

    for i, e in enumerate(action):
        actor = e.killer
        if e.kind == "plant":
            # r6-dissect sometimes credits the plant to a defender; fall back to an alive attacker.
            attackers = 1 if info["our_role"] == "Defense" else 0
            attack_team = 0 if attackers == 1 else 1
            if actor not in team or team[actor] != attack_team:
                actor = next((u for u, a in alive.items() if a and team[u] == attack_team), actor)
            shots.append(Shot(rnd, e.t - 6, e.t + 2, actor, "third", "plant", at=e.t))
            continue
        if actor not in lineup:
            continue
        mates_alive = sum(1 for u, a in alive.items() if a and team[u] == team[actor])
        foes_alive = sum(1 for u, a in alive.items() if a and team[u] != team[actor])
        clutch = (mates_alive == 1 and foes_alive >= 2) or actor in clutching
        if clutch:
            clutching.add(actor)  # stay on the clutch camera for the rest of the round
        shots.append(Shot(rnd, e.t - LEAD, e.t + TAIL, actor,
                          "third" if clutch else "pov", "clutch" if clutch else "kill", at=e.t))
        if e.victim in alive:
            alive[e.victim] = False

        # Multi-kill instant replay after the last kill in the streak.
        streak = [x for x in action[: i + 1] if x.kind == "kill" and x.killer == actor and e.t - x.t <= MULTI_WINDOW]
        nxt = action[i + 1] if i + 1 < len(action) else None
        streak_ends = not (nxt and nxt.kind == "kill" and nxt.killer == actor and nxt.t - e.t <= MULTI_WINDOW)
        if len(streak) >= 2 and streak_ends:
            shots.append(Shot(rnd, streak[0].t - 2, e.t + 1, actor, "pov", "multikill-replay", slowmo=True))

    return _clean(shots)


def _clean(shots: list[Shot]) -> list[Shot]:
    """Resolve overlaps (later action wins), merge same-camera neighbours, drop tiny shots.
    Replays are kept as separate inserts and not merged."""
    live = sorted((s for s in shots if not s.slowmo), key=lambda s: s.start)
    out: list[Shot] = []
    for s in live:
        s.start = max(s.start, 0)
        # Never cut away before the previous shot's key moment has played.
        if out and out[-1].at is not None:
            s.start = max(s.start, out[-1].at + 0.5)
        if out and s.start < out[-1].end:
            out[-1].end = s.start
            if out[-1].end - out[-1].start < MIN_SHOT:
                out.pop()
        if out and out[-1].player == s.player and out[-1].view == s.view and s.start - out[-1].end < MAX_GAP:
            out[-1].end = s.end
            continue
        out.append(s)
    result: list[Shot] = []
    for s in out:
        result.append(s)
        result += [r for r in shots if r.slowmo and abs(r.end - s.end) < TAIL + 1.01]
    return result


def direct(match: Match) -> list[Shot]:
    rounds = sorted({e.round for e in match.events if e.round})
    return [s for r in rounds for s in direct_round(match, r)]


def passes(shots: list[Shot]) -> list[dict]:
    """Unique (round, player, view) recordings the capture stage must make."""
    seen = sorted({(s.round, s.player, s.view) for s in shots})
    return [{"round": r, "player": p, "view": v} for r, p, v in seen]


def save(shots: list[Shot], path) -> None:
    path.write_text(json.dumps({"shots": [asdict(s) for s in shots], "passes": passes(shots)}, indent=2))
