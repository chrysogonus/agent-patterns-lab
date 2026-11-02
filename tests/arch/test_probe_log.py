"""The probe log: A2's memory on the signal trace (specs/009 contracts/architectures.md)."""

import json
import random

from apl.arch.probe_log import ProbeLog
from apl.signal_trace import DEV_SEEDS, generate, start_episode
from apl.signal_trace.strategy import suspects
from apl.signal_trace.tools import AgentTools

LAYOUT = {
    "segments": 64,
    "runs": [
        {"from": "S", "first": 1, "last": 18},
        {"from": 18, "first": 19, "last": 30},
        {"from": 30, "first": 31, "last": 37},
        {"from": 30, "first": 38, "last": 45},
        {"from": 18, "first": 46, "last": 64},
    ],
}


def _start(layout: dict[str, object]) -> str:
    return json.dumps({"ok": True, "error": None, "data": layout})


def _probe(log: ProbeLog, segment: int, water: bool) -> None:
    result = {"ok": True, "error": None, "data": {"segment": segment, "water": water}}
    log.apply("probe", {"segment": segment}, result)


def test_the_render_matches_the_contract() -> None:
    log = ProbeLog.from_start(_start(LAYOUT))
    assert log.render() == (
        "Pipe: 64 segments.\n"
        "Runs: S → 1–18; 18 → 19–30; 30 → 31–37; 30 → 38–45; 18 → 46–64\n"
        "Probes so far: none."
    )
    _probe(log, 32, False)
    _probe(log, 18, True)
    _probe(log, 25, False)
    assert log.render().splitlines()[-1] == "Probes so far (3, in order): 32 dry, 18 wet, 25 dry."
    assert log.known == 3


def test_failed_calls_change_nothing_and_look_replaces_the_runs() -> None:
    log = ProbeLog.from_start(_start(LAYOUT))
    error = {"ok": False, "error": {"code": "no_such_segment", "message": "x"}, "data": None}
    log.apply("probe", {"segment": 99}, error)
    log.apply("submit", {"segment": 3}, {"ok": True, "error": None, "data": {"submitted": 3}})
    assert log.answers == [] and log.known == 0
    straight = {"segments": 8, "runs": [{"from": "S", "first": 1, "last": 8}]}
    log.apply("look", {}, {"ok": True, "error": None, "data": straight})
    assert log.render().splitlines()[:2] == ["Pipe: 8 segments.", "Runs: S → 1–8"]


def test_repeats_count_once_in_known() -> None:
    log = ProbeLog.from_start(_start(LAYOUT))
    _probe(log, 5, True)
    _probe(log, 5, True)
    assert log.known == 1 and len(log.answers) == 2


def test_its_suspects_agree_with_the_environment() -> None:
    rng = random.Random("probe-log")
    for seed in DEV_SEEDS:
        pipe = generate("T3", seed)
        tools = AgentTools(start_episode(pipe))
        log = ProbeLog.from_start(json.dumps(tools.start.to_dict()))
        answers = []
        for _ in range(6):
            k = rng.randint(1, 64)
            _probe(log, k, pipe.wet(k))
            answers.append((k, pipe.wet(k)))
            assert log.suspects() == suspects(pipe.feeder, answers)
