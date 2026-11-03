"""A4 in runs, reports and the comparison (specs/007 US3, SC-007, SC-008)."""

import json
from pathlib import Path

import pytest

from apl.runner import registry, run
from apl.runner.report import load_run, render
from apl.runner.run import continue_run, execute, plan_continue
from apl.runner.settings import Settings
from apl.runner.spec import RunSpec
from tests.runner.scripted import raise_error, scripted_factory, text_answer, then
from tests.runner.test_continue import CODE
from tests.runner.test_plan_execute_runs import PROBLEMS, _execute


@pytest.fixture(autouse=True)
def _clean_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, "code_version", lambda: dict(CODE))


@pytest.mark.parametrize("problem", sorted(PROBLEMS))
def test_a4_joins_an_earlier_run_with_its_attempts(tmp_path: Path, problem: str) -> None:
    archs, level = PROBLEMS[problem]
    earlier = _execute(tmp_path / "earlier", archs, level, problem)
    a4 = _execute(tmp_path / "a4", ["reflexion"], level, problem)
    report = render([load_run(earlier), load_run(a4)])  # acceptance 3.2, SC-007
    section = report[report.index("## Comparison") : report.index("## Attempts")]
    assert any(
        line.startswith("| reflexion |") and line.endswith("| mapstate |")
        for line in section.splitlines()
    )
    attempts = report[report.index("## Attempts") :]
    assert f"| reflexion | {level} | 3 | 3 |" in attempts  # it gave up three times (3.3)
    assert f"| mapstate | {level} | 1 | 1 |" in attempts  # rows without attempts had one
    plain = render([load_run(earlier)])  # acceptance 3.4: older runs report as before
    assert "## Attempts" not in plain


@pytest.mark.parametrize("problem", sorted(PROBLEMS))
def test_an_interrupted_a4_run_continues(tmp_path: Path, problem: str) -> None:
    _, level = PROBLEMS[problem]
    archs = ["mapstate", "reflexion"]
    plays = {name: registry.load(name) for name in archs}
    spec = RunSpec.build(archs, [level], "dev", limit=2, problem=problem)
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
    assert {r["arch"]: r["attempts"] for r in rows if r["status"] == "completed"} == {
        "mapstate": None,
        "reflexion": 3,
    }


@pytest.mark.parametrize("problem", sorted(PROBLEMS))
def test_a_dry_run_lists_a4_and_calls_no_model(
    problem: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:  # acceptance 3.1, SC-008
    from apl.cli import main

    def no_model(*args: object) -> None:
        raise AssertionError("a dry run must not build a model")

    monkeypatch.setattr(run, "default_model_factory", no_model)
    monkeypatch.chdir(tmp_path)
    args = ["run", "--arch", "reflexion", "--level", "all", "--seeds", "dev", "--limit", "1"]
    assert main(args + (["--problem", problem] if problem == "survey" else [])) == 0
    out = capsys.readouterr().out
    assert "architectures  reflexion\n" in out and "not written yet" not in out
    assert list(tmp_path.iterdir()) == []
