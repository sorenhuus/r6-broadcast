import json

from r6cast.director import direct, passes
from r6cast.events import Event, Match


def _match():
    lineup = {"me": {"team": 1, "op": "Bandit"}, "mate": {"team": 1, "op": "Vigil"},
              "foe1": {"team": 0, "op": "Ash"}, "foe2": {"team": 0, "op": "Glaz"}}
    m = Match("x", 0, meta={"recording_player": "me"})
    m.events = [
        Event(0, "round_start", round=1, note=json.dumps({"our_role": "Defense", "lineup": lineup})),
        Event(50, "kill", round=1, killer="foe1", victim="mate"),
        Event(80, "kill", round=1, killer="me", victim="foe1"),
        Event(84, "kill", round=1, killer="me", victim="foe2"),
        Event(87, "round_end", round=1, score="1-0"),
    ]
    return m


def test_shots_follow_killers_without_overlap():
    shots = direct(_match())
    live = [s for s in shots if not s.slowmo]
    assert [s.player for s in live] == ["me", "foe1", "me"]
    for a, b in zip(live, live[1:]):
        assert a.end <= b.start


def test_clutch_goes_third_person_and_multikill_gets_replay():
    shots = direct(_match())
    assert any(s.tag == "clutch" and s.view == "third" for s in shots)
    assert any(s.tag == "multikill-replay" and s.slowmo for s in shots)
    assert {(p["player"], p["view"]) for p in passes(shots)} >= {("me", "third"), ("foe1", "pov")}
