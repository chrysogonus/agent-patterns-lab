"""Warehouse runs: plan, refuse, interrupt, continue, rows (specs/012 US3, contracts/results.md)."""

import json
from pathlib import Path

import pytest

from apl.cli import main
from apl.runner import registry, run
from apl.runner.run import continue_run, execute, plan_continue
from apl.runner.settings import Settings
from apl.runner.spec import RunSpec
from apl.warehouse import generate
from tests.runner.scripted import raise_error, scripted_factory, text_answer, then
from tests.runner.test_continue import CODE

ARCHS = ["react", "mapstate"]
FIELDS = ("delivered", "packages", "idle_robot_turns", "parallel_turns", "reference_is_optimal")


@pytest.fixture(autouse=True)
def _clean_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, "code_version", lambda: dict(CODE))


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in (path / "episodes.jsonl").read_text().splitlines()]


def test_the_dry_run_plans_every_architecture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    archs = "react,mapstate,fanout,rounds,blackboard"
    command = ["run", "--problem", "warehouse", "--arch", archs, "--level", "all"]
    assert main([*command, "--seeds", "dev", "--limit", "1"]) == 0
    out = capsys.readouterr().out
    assert "problem        warehouse" in out and "levels         P1, P2, P3" in out
    assert "episodes       15" in out
    assert not (tmp_path / "results").exists()


def test_an_architecture_that_does_not_play_it_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    command = ["run", "--problem", "warehouse", "--arch", "hybrid", "--level", "P1"]
    assert main([*command, "--seeds", "dev"]) == 2
    assert capsys.readouterr().err == (
        "apl: hybrid does not play the warehouse problem "
        "(it plays: dungeon, rune, signal, workshop)\n"
    )


def test_an_interrupted_warehouse_run_continues(tmp_path: Path) -> None:  # US3 3
    plays = {name: registry.load(name) for name in ARCHS}
    spec = RunSpec.build(ARCHS, ["P1"], "dev", limit=2, problem="warehouse")
    first = execute(
        spec, Settings(), results_dir=tmp_path, architectures=plays,
        model_factory=scripted_factory(then(text_answer(), 2, raise_error(KeyboardInterrupt()))),
    )  # fmt: skip
    assert first.exit_code == 130
    plan = plan_continue(
        first.path, Settings(), code=CODE, versions=run.package_versions(),
        written={name: True for name in ARCHS},
    )  # fmt: skip
    assert not plan.refusals and len(plan.done) == 2 and len(plan.left) == 2
    done = continue_run(
        plan, Settings(), model_factory=scripted_factory(text_answer()), architectures=plays
    )
    assert done.exit_code == 0
    rows = _rows(first.path)
    for row in rows:
        floor = generate("P1", int(str(row["seed"])))
        assert row["problem"] == "warehouse" and all(f in row for f in FIELDS)
        assert row["optimal_steps"] == floor.reference_steps and row["budget"] == floor.budget
        assert row["delivered"] == 0 and row["packages"] == 3 and row["end_reason"] == "stopped"
        assert row["reference_is_optimal"] is False


def test_two_architectures_get_the_same_prompt_and_budget(tmp_path: Path) -> None:  # US4 3
    plays = {name: registry.load(name) for name in ARCHS}
    spec = RunSpec.build(ARCHS, ["P2"], "dev", limit=1, problem="warehouse")
    outcome = execute(
        spec, Settings(), results_dir=tmp_path, architectures=plays,
        model_factory=scripted_factory(text_answer()),
    )  # fmt: skip
    rows = _rows(outcome.path)
    assert len({r["budget"] for r in rows}) == 1 and len(rows) == 2
    record = json.loads((outcome.path / "run.json").read_text())
    from apl.warehouse.prompt import prompt_fingerprint

    assert record["settings"]["prompt_fingerprint"] == prompt_fingerprint()
