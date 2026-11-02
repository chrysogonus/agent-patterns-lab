"""Episode rows and the settings record (contracts/results.md)."""

import json

import pytest

from apl.dungeon import generate, start_episode
from apl.runner.meter import Meter
from apl.runner.results import EpisodeRow, RunRecord
from apl.runner.spec import EpisodeKey

KEY = EpisodeKey("react", "L1", 1000, 1)


def _meter(calls: int = 3, tokens: tuple[int, int] = (100, 20), missing: bool = False) -> Meter:
    episode = start_episode(generate("L1", 1000))
    meter = Meter(episode, token_cap=1000)
    meter.llm_calls, (meter.input_tokens, meter.output_tokens) = calls, tokens
    meter.usage_missing = missing
    return meter


def _completed(actions: int, success: bool, missing: bool = False) -> EpisodeRow:
    dungeon = generate("L1", 1000)
    episode = start_episode(dungeon)
    for action in dungeon.solution.actions[:actions] if success else []:
        getattr(episode, action.tool)(*action.args)
    if not success:
        episode.move("up")
        episode.stop()
    meter = _meter(missing=missing)
    return EpisodeRow.completed(KEY, "run-1", "dev", episode.outcome(), meter, 2.345, None)


def test_completed_row() -> None:
    dungeon = generate("L1", 1000)
    row = _completed(dungeon.solution.length, success=True)
    assert row.status == "completed" and row.success and row.end_reason == "exit"
    assert row.steps == row.optimal_steps == dungeon.solution.length
    assert row.efficiency == 1.0 and row.budget == dungeon.budget
    assert (row.llm_calls, row.input_tokens, row.output_tokens) == (3, 100, 20)
    assert row.tool_calls == dungeon.solution.length and row.latency_s == 2.3
    assert row.budget_hit is False and row.token_cap_hit is False
    assert row.output_limit_hits == 0


def test_failed_episode_has_no_efficiency() -> None:
    row = _completed(0, success=False)
    assert row.success is False and row.end_reason == "stopped" and row.efficiency is None
    assert row.invalid_actions == 1 and row.steps == 1


def test_efficiency_is_rounded() -> None:
    dungeon = generate("L1", 1000)
    episode = start_episode(dungeon)
    episode.look()
    for action in dungeon.solution.actions:
        getattr(episode, action.tool)(*action.args)
    row = EpisodeRow.completed(KEY, "r", "dev", episode.outcome(), _meter(), 1.0, None)
    assert row.efficiency == round(dungeon.solution.length / (dungeon.solution.length + 1), 3)


def test_missing_usage_gives_unknown_tokens() -> None:
    row = _completed(0, success=False, missing=True)
    assert row.input_tokens is None and row.output_tokens is None


def test_error_row() -> None:
    episode = start_episode(generate("L1", 1000))
    row = EpisodeRow.failed(
        KEY, "run-1", "dev", episode, _meter(1), 0.5, "RateLimitError: slow down"
    )
    assert row.status == "error" and row.error == "RateLimitError: slow down"
    assert row.optimal_steps == episode.dungeon.solution.length and row.budget > 0
    for name in ("success", "end_reason", "steps", "efficiency", "invalid_actions"):
        assert getattr(row, name) is None
    assert row.budget_hit is None and row.token_cap_hit is None


def test_row_key_order_matches_the_contract() -> None:
    assert list(_completed(0, success=False).to_dict()) == [
        "run_id", "arch", "level", "seed", "seed_set", "repeat", "status", "success",
        "end_reason", "steps", "optimal_steps", "budget", "efficiency", "invalid_actions",
        "budget_hit", "token_cap_hit", "output_limit_hits", "llm_calls", "tool_calls",
        "input_tokens", "output_tokens", "latency_s", "arch_error", "error", "scouts",
        "orchestrator_calls", "problem", *SURVEY_FIELDS,  # specs/005: added at the end
        "attempts",  # specs/007
        "submitted_segment", "broken_segment", "segments", "probes", "wasted_probes",  # specs/009
        "traps", "repeated_traps", "walks",  # specs/010
        "stuck", "wasted", "inspected", "crafted",  # specs/011
    ]  # fmt: skip


def test_parse_round_trips_and_validates() -> None:
    row = _completed(0, success=False)
    data = json.loads(json.dumps(row.to_dict()))
    assert EpisodeRow.parse(data) == row
    for broken, field in [
        ({**data, "steps": "3"}, "steps"),
        ({**data, "seed": True}, "seed"),
        ({**data, "status": "fine"}, "status"),
        ({k: v for k, v in data.items() if k != "budget"}, "budget"),
        ({**data, "extra": 1}, "extra"),
        ({**data, "arch": None}, "arch"),
    ]:
        with pytest.raises(ValueError, match=field):
            EpisodeRow.parse(broken)


def test_rows_from_before_the_output_limit_count_parse() -> None:
    data = json.loads(json.dumps(_completed(0, success=False).to_dict()))
    del data["output_limit_hits"]
    assert EpisodeRow.parse(data).output_limit_hits is None


def test_run_record_round_trips() -> None:
    record = RunRecord(
        run_id="20261030-151200-react",
        started="2026-10-30T15:12:00+01:00",
        ended=None,
        completed=False,
        architectures=("react",),
        levels=("L1", "L2"),
        seed_set="dev",
        seeds=(1000, 1001),
        repeats=2,
        settings={"model": "openai:gpt-6-luna", "token_cap": 600000},
        code={"commit": None, "dirty": None},
        versions={"python": "3.12.13"},
    )
    data = json.loads(json.dumps(record.to_dict()))
    assert data["levels"] == ["L1", "L2"]
    assert RunRecord.parse(data) == record
    with pytest.raises(ValueError, match="seed_set"):
        RunRecord.parse({k: v for k, v in data.items() if k != "seed_set"})


def test_rows_record_scouts_and_orchestrator_calls() -> None:  # specs/004 contracts/results.md
    row = _completed(0, success=False)  # one failed move, then stopped
    assert (row.scouts, row.orchestrator_calls) == (1, 0)
    episode = start_episode(generate("L1", 1000))
    error = EpisodeRow.failed(KEY, "run-1", "dev", episode, _meter(), 0.5, "x")
    assert error.scouts is None and error.orchestrator_calls == 0


def test_rows_from_before_m4_parse() -> None:
    data = json.loads(json.dumps(_completed(0, success=False).to_dict()))
    del data["scouts"], data["orchestrator_calls"]
    row = EpisodeRow.parse(data)
    assert row.scouts is None and row.orchestrator_calls is None


SURVEY_FIELDS = (
    "submitted_total", "true_total", "cells_seen", "cells", "parallel_turns",
    "reference_is_optimal",
)  # fmt: skip


def test_rows_and_records_without_a_problem_are_dungeon_ones() -> None:
    row = _completed(3, success=False).to_dict()
    assert row["problem"] == "dungeon" and all(row[f] is None for f in SURVEY_FIELDS)
    for name in ("problem", *SURVEY_FIELDS):
        del row[name]
    parsed = EpisodeRow.parse(row)
    assert parsed.problem == "dungeon" and parsed.parallel_turns is None
    record = RunRecord(
        "r", "s", None, False, ("react",), ("L1",), "dev", (1000,), 1, {}, {}, {}
    ).to_dict()
    assert record["problem"] == "dungeon"
    del record["problem"]
    assert RunRecord.parse(record).problem == "dungeon"


def test_survey_fields_round_trip_and_are_type_checked() -> None:
    row = _completed(3, success=False).to_dict() | {
        "submitted_total": 12, "true_total": 15, "cells_seen": 80, "cells": 100,
        "parallel_turns": 40, "reference_is_optimal": True,
    }  # fmt: skip
    parsed = EpisodeRow.parse(json.loads(json.dumps(row)))
    assert (parsed.submitted_total, parsed.true_total, parsed.reference_is_optimal) == (
        12, 15, True,
    )  # fmt: skip
    with pytest.raises(ValueError, match="field 'parallel_turns' must be int"):
        EpisodeRow.parse(row | {"parallel_turns": "40"})
    with pytest.raises(ValueError, match="field 'reference_is_optimal' must be bool"):
        EpisodeRow.parse(row | {"reference_is_optimal": 1})
    with pytest.raises(ValueError, match="field 'problem' must be one of"):
        EpisodeRow.parse(row | {"problem": "chess"})
