"""One signal-trace episode (specs/009 data-model.md, research R6–R9)."""

import dataclasses

import pytest

from apl.signal_trace import generate, start_episode
from apl.signal_trace.env import MAX_ATTEMPTS, Episode
from apl.signal_trace.model import Pipe
from apl.signal_trace.results import ErrorCode
from apl.signal_trace.strategy import informative, suspects


def _t1(broken: int = 9) -> Pipe:
    return dataclasses.replace(generate("T1", 1000), broken=broken)


def _episode(broken: int = 9, attempts: int = 1) -> Episode:
    episode = start_episode(_t1(broken))
    episode.max_attempts = attempts
    return episode


def test_the_layout_is_free_and_look_repeats_it_for_a_step() -> None:
    episode = _episode()
    view = episode.describe().to_dict()
    assert view == {"segments": 16, "runs": [{"from": "S", "first": 1, "last": 16}]}
    assert episode.steps == 0
    result = episode.look()
    assert result.ok and result.to_dict()["data"] == view and episode.steps == 1


@pytest.mark.parametrize("raw", [8, "8", 9, "16", 1])
def test_probe_answers_follow_the_rule(raw: object) -> None:
    episode = _episode(broken=9)
    k = int(str(raw))
    data = episode.probe(raw).to_dict()
    assert data == {"ok": True, "error": None, "data": {"segment": k, "water": k < 9}}
    assert episode.probes == 1 and episode.invalid_actions == 0


@pytest.mark.parametrize("raw", [0, 17, "S", 1.5, True, "about 3", None, -2])
def test_a_bad_segment_costs_a_step_and_is_not_a_probe(raw: object) -> None:
    episode = _episode()
    result = episode.probe(raw)
    assert not result.ok and result.error is not None
    assert result.error.code == ErrorCode.NO_SUCH_SEGMENT
    assert result.error.message == f"{raw!r} is not a segment; segments are numbered 1 to 16."
    assert episode.steps == 1 and episode.invalid_actions == 1 and episode.probes == 0
    assert episode.end_reason is None
    assert not episode.submit(raw).ok and episode.end_reason is None


def test_the_right_submission_succeeds() -> None:
    episode = _episode(broken=9)
    episode.probe(8)
    assert episode.submit(9).to_dict()["data"] == {"submitted": 9}
    outcome = episode.outcome()
    assert outcome.success and str(outcome.end_reason) == "submitted"
    assert outcome.submitted_segment == outcome.broken_segment == 9


def test_a_wrong_submission_fails_without_attempts_left() -> None:
    episode = _episode(broken=9)
    assert episode.submit("10").ok
    outcome = episode.outcome()
    assert not outcome.success and outcome.submitted_segment == 10


def test_a_wrong_submission_restarts_a_retrying_architecture() -> None:
    episode = _episode(broken=9, attempts=MAX_ATTEMPTS)
    restarts: list[int] = []
    episode.on_restart = lambda: restarts.append(episode.attempt)
    episode.probe(4)
    data = episode.submit(10).to_dict()["data"]
    assert data == {"submitted": 10, "correct": False, "attempts_left": 2}
    assert restarts == [2] and episode.attempt == 2 and episode.end_reason is None
    assert episode.answers == [] and episode.steps == 2
    episode.probe(4)  # not wasted: the answers were cleared
    assert episode.wasted_probes == 0
    episode.submit(11)
    episode.submit(12)
    assert episode.end_reason is not None and episode.attempt == 3
    outcome = episode.outcome()
    assert not outcome.success and outcome.attempts == 3 and outcome.submitted_segment == 12
    assert outcome.to_dict()["attempts"] == 3


def test_the_budget_ends_the_episode_and_a_last_submission_counts_first() -> None:
    episode = _episode(broken=9)
    for _ in range(15):
        episode.probe(1)
    assert episode.submit(9).ok
    assert str(episode.outcome().end_reason) == "submitted" and episode.outcome().success
    other = _episode(broken=9)
    for _ in range(16):
        other.probe(1)
    assert str(other.outcome().end_reason) == "budget" and other.outcome().budget_hit


def test_calls_after_the_end_are_not_counted() -> None:
    episode = _episode()
    episode.stop()
    result = episode.probe(3)
    assert result.error is not None and result.error.code == ErrorCode.EPISODE_OVER
    assert episode.steps == 0 and episode.log[-1].step is None
    assert str(episode.outcome().end_reason) == "stopped"


def test_wasted_probes() -> None:
    episode = _episode(broken=9)
    episode.probe(6)  # wet: 1–6 clear
    episode.probe(12)  # dry: the break is on 7–12
    assert episode.wasted_probes == 0
    episode.probe(6)  # a repeat
    episode.probe(3)  # upstream of a known wet segment
    episode.probe(14)  # downstream of a known dry segment
    assert episode.wasted_probes == 3 and episode.probes == 5
    assert [e.wasted for e in episode.log] == [False, False, True, True, True]
    assert "wasted" not in episode.log[0].to_dict() and episode.log[2].to_dict()["wasted"]
    assert episode.suspects() == frozenset(range(7, 13))


def test_an_unknown_tool_costs_a_step() -> None:
    episode = _episode()
    result = episode.unknown("scan")
    assert result.error is not None and result.error.code == ErrorCode.UNKNOWN_TOOL
    assert result.error.message == (
        "There is no tool named 'scan'. The tools are look, probe and submit."
    )
    assert episode.steps == 1 and episode.invalid_actions == 1


def test_the_outcome_dict() -> None:
    episode = _episode(broken=9)
    episode.probe(8)
    episode.probe(8)
    episode.submit(9)
    data = episode.outcome().to_dict()
    assert {k: v for k, v in data.items() if k != "log"} == {
        "level": "T1", "seed": 1000, "success": True, "end_reason": "submitted", "steps": 3,
        "optimal_steps": 5, "budget": 16, "invalid_actions": 0, "budget_hit": False,
        "submitted_segment": 9, "broken_segment": 9, "segments": 16, "probes": 2,
        "wasted_probes": 1, "reference_is_optimal": True,
    }  # fmt: skip
    log = data["log"]
    assert isinstance(log, list) and log[0] == {
        "index": 0, "step": 1, "action": {"tool": "probe", "args": ["8"]},
        "result": {"ok": True, "error": None, "data": {"segment": 8, "water": True}},
    }  # fmt: skip


def test_wasted_probes_are_reproduced_from_the_saved_log() -> None:  # SC-006
    pipe = _t1(broken=9)
    episode = start_episode(pipe)
    episode.max_attempts = MAX_ATTEMPTS
    for raw in (6, 12, 6, 3, 14, "S"):
        episode.probe(raw)
    episode.submit(10)  # wrong: a restart, the answers start again
    for raw in (6, 6, 8):
        episode.probe(raw)
    episode.submit(9)
    saved = episode.outcome().to_dict()
    answers: dict[int, list[tuple[int, bool]]] = {}
    wasted = 0
    log = saved["log"]
    assert isinstance(log, list)
    for entry in log:
        result, attempt = entry["result"], entry.get("attempt", 1)
        if entry["action"]["tool"] != "probe" or not result["ok"]:
            continue
        k, water = result["data"]["segment"], result["data"]["water"]
        so_far = answers.setdefault(attempt, [])
        wasted += not informative(pipe.feeder, suspects(pipe.feeder, so_far), k)
        so_far.append((k, water))
    assert wasted == saved["wasted_probes"] == 4


@pytest.mark.parametrize("tool", ["probe", "submit"])
def test_a_very_long_number_is_no_segment(tool: str) -> None:
    episode = _episode()
    raw = "9" * 5000
    result = getattr(episode, tool)(raw)
    assert result.error is not None and result.error.code == ErrorCode.NO_SUCH_SEGMENT
    assert episode.steps == 1 and episode.invalid_actions == 1 and len(episode.log) == 1
    assert episode.end_reason is None
