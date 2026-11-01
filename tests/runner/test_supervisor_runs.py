"""A5 in runs, reports and the comparison (specs/008 US3, SC-006, SC-007)."""

import json
from pathlib import Path

import pytest

from apl.runner import registry, run
from apl.runner.report import load_run, render
from apl.runner.run import continue_run, execute, plan_continue
from apl.runner.settings import Settings
from apl.runner.spec import RunSpec
from tests.runner.scripted import raise_error, scripted_factory, text_answer, then
from tests.runner.test_compare import ARCHS
from tests.runner.test_continue import CODE
from tests.runner.test_plan_execute_runs import _execute


@pytest.fixture(autouse=True)
def _clean_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, "code_version", lambda: dict(CODE))


def test_a5_joins_an_earlier_run_in_one_report(tmp_path: Path) -> None:  # SC-007, US3 4
    earlier = _execute(tmp_path / "earlier", ARCHS, "L1", "dungeon")
    a5 = _execute(tmp_path / "a5", ["supervisor"], "L1", "dungeon")
    report = render([load_run(earlier), load_run(a5)])
    section = report[report.index("## Comparison") :]
    names = [line.split(" | ")[0].removeprefix("| ") for line in section.splitlines()]
    assert sorted(n for n in names if n in [*ARCHS, "supervisor"]) == sorted([*ARCHS, "supervisor"])
    assert any(
        line.startswith("| supervisor |") and line.endswith("| mapstate |")
        for line in section.splitlines()
    )


def test_an_interrupted_a5_run_continues(tmp_path: Path) -> None:  # US3 3
    archs = ["mapstate", "supervisor"]
    plays = {name: registry.load(name) for name in archs}
    spec = RunSpec.build(archs, ["L1"], "dev", limit=2)
    first = execute(
        spec, Settings(), results_dir=tmp_path, architectures=plays,
        model_factory=scripted_factory(then(text_answer(), 4, raise_error(KeyboardInterrupt()))),
    )  # fmt: skip
    assert first.exit_code == 130
    plan = plan_continue(
        first.path, Settings(), code=CODE, versions=run.package_versions(),
        written={name: True for name in archs},
    )  # fmt: skip
    assert not plan.refusals and plan.left and len(plan.done) + len(plan.left) == 4
    done = continue_run(
        plan, Settings(), model_factory=scripted_factory(text_answer()), architectures=plays
    )
    assert done.exit_code == 0
    rows = [json.loads(line) for line in (first.path / "episodes.jsonl").read_text().splitlines()]
    finished = [r for r in rows if r["status"] == "completed"]
    assert sorted({r["arch"] for r in finished}) == archs and len(finished) == 4


def test_a_dry_run_lists_a5_and_calls_no_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:  # US3 1, SC-006
    from apl.cli import main

    def no_model(*args: object) -> None:
        raise AssertionError("a dry run must not build a model")

    monkeypatch.setattr(run, "default_model_factory", no_model)
    monkeypatch.chdir(tmp_path)
    args = ["run", "--arch", "supervisor", "--level", "all", "--seeds", "dev", "--limit", "1"]
    assert main(args) == 0
    out = capsys.readouterr().out
    assert "architectures  supervisor\n" in out and "not written yet" not in out
    assert list(tmp_path.iterdir()) == []


def test_a_survey_run_of_a5_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:  # US3 2
    from apl.cli import main

    monkeypatch.chdir(tmp_path)
    args = [
        "run",
        "--problem",
        "survey",
        "--arch",
        "supervisor",
        "--level",
        "all",
        "--seeds",
        "dev",
    ]
    assert main(args) != 0
    captured = capsys.readouterr()
    assert "supervisor does not play the survey problem (it plays: dungeon)" in (
        captured.out + captured.err
    )
    assert list(tmp_path.iterdir()) == []
