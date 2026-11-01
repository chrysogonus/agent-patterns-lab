"""Continuing an interrupted run (specs/004 contracts/cli.md, research R11, R12; SC-004)."""

import json
from pathlib import Path
from typing import Any

import pytest

from apl.runner import registry, run
from apl.runner.results import EpisodeRow
from apl.runner.run import ContinuePlan, continue_run, execute, plan_continue
from apl.runner.settings import Settings
from apl.runner.spec import RunSpec
from tests.runner.scripted import Strategy, raise_error, scripted_factory, text_answer, then

ARCHS = ["react", "mapstate", "mapstate_routes", "hybrid", "fanout", "rounds", "blackboard"]
CODE = {"commit": "abc1234", "dirty": False}
WRITTEN = {name: True for name in ARCHS}


@pytest.fixture(autouse=True)
def _clean_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, "code_version", lambda: dict(CODE))


def _plays() -> dict[str, Any]:
    return {name: registry.load(name) for name in ARCHS}


def _start(tmp_path: Path, strategy: Strategy) -> run.RunOutcome:
    spec = RunSpec.build(ARCHS, ["all"], "dev", limit=1)
    return execute(
        spec,
        Settings(),
        model_factory=scripted_factory(strategy),
        architectures=_plays(),
        results_dir=tmp_path,
    )


def _plan(path: Path, **changes: Any) -> ContinuePlan:
    return plan_continue(
        path,
        changes.get("settings", Settings()),
        code=changes.get("code", CODE),
        versions=changes.get("versions", run.package_versions()),
        written=changes.get("written", WRITTEN),
    )


def _continue(plan: ContinuePlan, strategy: Strategy) -> run.RunOutcome:
    return continue_run(
        plan, Settings(), model_factory=scripted_factory(strategy), architectures=_plays()
    )


def _rows(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in (path / "episodes.jsonl").read_text().splitlines()]
    return [{k: v for k, v in r.items() if k not in ("run_id", "latency_s")} for r in rows]


def test_interrupted_twice_and_continued_equals_an_uninterrupted_run(tmp_path: Path) -> None:
    whole = _start(tmp_path / "whole", text_answer())
    first = _start(tmp_path / "parts", then(text_answer(), 5, raise_error(KeyboardInterrupt())))
    assert first.exit_code == 130
    plan = _plan(first.path)
    assert not plan.refusals and 0 < len(plan.done) < 21
    second = _continue(plan, then(text_answer(), 12, raise_error(KeyboardInterrupt())))
    assert second.exit_code == 130 and second.path == first.path
    plan = _plan(first.path)
    assert len(plan.done) > 5 and plan.left
    last = _continue(plan, text_answer())
    assert last.exit_code == 0 and last.record.completed and last.record.ended
    assert sorted(map(str, _rows(first.path))) == sorted(map(str, _rows(whole.path)))
    keys = [(r["arch"], r["level"]) for r in _rows(first.path)]
    assert len(keys) == len(set(keys)) == 21
    assert _plan(first.path).complete


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            {"settings": Settings(token_cap=1000)},
            "setting token_cap differs (run: 2000000, now: 1000)",
        ),
        ({"versions": {"langgraph": "0.0.1"}}, "version of langgraph differs"),
        (
            {"code": {"commit": "fff0000", "dirty": False}},
            "commit differs (run: abc1234, now: fff0000)",
        ),
        (
            {"code": {"commit": "abc1234", "dirty": True}},
            "the working tree has uncommitted changes",
        ),
        ({"written": {**WRITTEN, "rounds": False}}, "architecture rounds is not written yet"),
    ],
)
def test_refusals_name_the_difference_and_write_nothing(
    tmp_path: Path, change: dict[str, Any], message: str
) -> None:
    started = _start(tmp_path, then(text_answer(), 3, raise_error(KeyboardInterrupt())))
    before = {p: p.read_bytes() for p in started.path.rglob("*") if p.is_file()}
    plan = _plan(started.path, **change)
    assert any(message in r for r in plan.refusals), plan.refusals
    assert {p: p.read_bytes() for p in started.path.rglob("*") if p.is_file()} == before


def test_a_run_started_dirty_cannot_be_continued(tmp_path: Path) -> None:
    started = _start(tmp_path, then(text_answer(), 3, raise_error(KeyboardInterrupt())))
    data = json.loads((started.path / "run.json").read_text())
    data["code"]["dirty"] = True
    (started.path / "run.json").write_text(json.dumps(data))
    plan = _plan(started.path, code={"commit": "fff0000", "dirty": True})
    assert "the run was started with uncommitted changes; it cannot be continued" in plan.refusals
    assert len(plan.refusals) == 3  # all differences together


def test_a_cut_off_row_is_removed_only_when_continuing(tmp_path: Path) -> None:
    started = _start(tmp_path, then(text_answer(), 3, raise_error(KeyboardInterrupt())))
    rows = started.path / "episodes.jsonl"
    rows.write_text(rows.read_text() + '{"run_id": "cut')
    plan = _plan(started.path)
    assert plan.cut_off and not plan.refusals
    assert rows.read_text().endswith('"cut')  # planning changes nothing
    _continue(plan, text_answer())
    assert all(EpisodeRow.parse(json.loads(line)) for line in rows.read_text().splitlines())
    assert len(rows.read_text().splitlines()) == 21


def test_error_rows_are_not_played_again(tmp_path: Path) -> None:
    from tests.runner.scripted import FakeProviderError

    started = _start(tmp_path, then(text_answer(), 1, raise_error(FakeProviderError(503))))
    assert started.exit_code == 4  # stopped after 3 errors in a row
    plan = _plan(started.path)
    errors = [k for k in plan.done if k.arch != "react"]
    assert len(errors) == 3 and all(k not in plan.left for k in errors)


def test_a_run_with_every_row_but_no_completion_is_completed(tmp_path: Path) -> None:  # FR-014
    whole = _start(tmp_path, text_answer())
    data = json.loads((whole.path / "run.json").read_text())
    data["completed"], data["ended"] = False, None  # a crash after the last row
    (whole.path / "run.json").write_text(json.dumps(data))
    plan = _plan(whole.path)
    assert not plan.complete and not plan.left and not plan.refusals
    outcome = _continue(plan, raise_error(AssertionError("nothing may be played")))
    assert outcome.exit_code == 0 and outcome.record.completed and outcome.record.ended
    assert json.loads((whole.path / "run.json").read_text())["completed"] is True


SURVEY_ARCHS = ["react", "mapstate", "fanout", "rounds", "blackboard"]


def test_a_survey_run_continues_on_the_survey_field(tmp_path: Path) -> None:
    spec = RunSpec.build(SURVEY_ARCHS, ["S1"], "dev", limit=1, problem="survey")
    plays = {name: registry.load(name) for name in SURVEY_ARCHS}
    first = execute(
        spec, Settings(), results_dir=tmp_path, architectures=plays,
        model_factory=scripted_factory(then(text_answer(), 2, raise_error(KeyboardInterrupt()))),
    )  # fmt: skip
    assert first.exit_code == 130
    record = json.loads((first.path / "run.json").read_text())
    assert record["problem"] == "survey"
    plan = plan_continue(
        first.path, Settings(), code=CODE, versions=run.package_versions(),
        written={name: True for name in SURVEY_ARCHS},
    )  # fmt: skip
    assert not plan.refusals and len(plan.done) + len(plan.left) == 5
    done = continue_run(
        plan, Settings(), model_factory=scripted_factory(text_answer()), architectures=plays
    )
    assert done.exit_code == 0
    rows = [json.loads(line) for line in (first.path / "episodes.jsonl").read_text().splitlines()]
    assert len(rows) == 5 and all(r["problem"] == "survey" for r in rows)
    assert all(r["true_total"] == 6 and r["cells"] == 36 for r in rows)


def test_an_older_run_without_a_problem_continues_as_a_dungeon_run(tmp_path: Path) -> None:
    first = _start(tmp_path, then(text_answer(), 3, raise_error(KeyboardInterrupt())))
    record = json.loads((first.path / "run.json").read_text())
    del record["problem"]
    (first.path / "run.json").write_text(json.dumps(record))
    plan = _plan(first.path)
    assert plan.record.problem == "dungeon" and not plan.refusals
    assert {k.level for k in plan.left} <= {"L1", "L2", "L3"}
