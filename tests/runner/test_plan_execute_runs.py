"""A3 in runs, reports and the comparison (specs/006 US3, SC-006, SC-007)."""

import json
from pathlib import Path
from typing import Any

import pytest

from apl.runner import registry, run
from apl.runner.report import load_run, render
from apl.runner.run import continue_run, execute, plan_continue
from apl.runner.settings import Settings
from apl.runner.spec import RunSpec
from tests.runner.scripted import raise_error, scripted_factory, text_answer, then
from tests.runner.test_compare import ARCHS, _ep, _report
from tests.runner.test_continue import CODE, SURVEY_ARCHS

PROBLEMS = {"dungeon": (ARCHS, "L1"), "survey": (SURVEY_ARCHS, "S1")}


@pytest.fixture(autouse=True)
def _clean_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, "code_version", lambda: dict(CODE))


def test_the_comparison_measures_a3_against_mapstate(tmp_path: Path) -> None:  # FR-014, 3.3
    rows = [
        _ep("mapstate", "L1", 8, True, input_tokens=50, output_tokens=10, llm_calls=4,
            orchestrator_calls=0, scouts=1, latency_s=1.0),
        _ep("plan_execute", "L1", 10, True, input_tokens=90, output_tokens=30, llm_calls=8,
            orchestrator_calls=2, scouts=1, latency_s=3.0),
    ]  # fmt: skip
    report = _report(tmp_path, rows)
    line = "| plan_execute | 100% | 0.80 | 10 | 120 | 2 / 6 | 3.0s | 1 | +0 pp | −0.20 | mapstate |"
    assert line in report  # acceptance 3.5: planning calls / executor calls


def _execute(tmp_path: Path, archs: list[str], level: str, problem: str, **settings: Any) -> Path:
    spec = RunSpec.build(archs, [level], "dev", limit=1, problem=problem)
    outcome = execute(
        spec, Settings(**settings), model_factory=scripted_factory(text_answer()),
        architectures={name: registry.load(name) for name in archs}, results_dir=tmp_path,
    )  # fmt: skip
    assert outcome.exit_code == 0
    return outcome.path


@pytest.mark.parametrize("problem", sorted(PROBLEMS))
def test_a3_joins_an_earlier_run_in_one_report(tmp_path: Path, problem: str) -> None:  # SC-007
    archs, level = PROBLEMS[problem]
    earlier = _execute(tmp_path / "earlier", archs, level, problem)
    a3 = _execute(tmp_path / "a3", ["plan_execute"], level, problem)
    report = render([load_run(earlier), load_run(a3)])
    section = report[report.index("## Comparison") :]
    names = [line.split(" | ")[0].removeprefix("| ") for line in section.splitlines()]
    assert sorted(n for n in names if n in [*archs, "plan_execute"]) == sorted(
        [*archs, "plan_execute"]
    )  # eight on the dungeon, six on the survey field
    assert any(line.startswith("| plan_execute |") and line.endswith("| mapstate |")
               for line in section.splitlines())  # fmt: skip
    other = _execute(tmp_path / "other", ["plan_execute"], level, problem, token_cap=1000)
    with pytest.raises(ValueError, match="token_cap differs"):  # acceptance 3.4
        render([load_run(earlier), load_run(other)])


@pytest.mark.parametrize("problem", sorted(PROBLEMS))
def test_an_interrupted_a3_run_continues(tmp_path: Path, problem: str) -> None:  # 3.2
    _, level = PROBLEMS[problem]
    archs = ["mapstate", "plan_execute"]
    plays = {name: registry.load(name) for name in archs}
    spec = RunSpec.build(archs, [level], "dev", limit=2, problem=problem)
    first = execute(
        spec, Settings(), results_dir=tmp_path, architectures=plays,
        model_factory=scripted_factory(then(text_answer(), 3, raise_error(KeyboardInterrupt()))),
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
    assert sorted((r["arch"], r["seed"]) for r in rows) == sorted(
        (a, s) for a in archs for s in spec.seeds
    )


@pytest.mark.parametrize("problem", sorted(PROBLEMS))
def test_a_dry_run_lists_a3_and_calls_no_model(
    problem: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:  # acceptance 3.1, SC-006
    from apl.cli import main

    def no_model(*args: object) -> None:
        raise AssertionError("a dry run must not build a model")

    monkeypatch.setattr(run, "default_model_factory", no_model)
    monkeypatch.chdir(tmp_path)
    args = ["run", "--arch", "plan_execute", "--level", "all", "--seeds", "dev", "--limit", "1"]
    assert main(args + (["--problem", problem] if problem == "survey" else [])) == 0
    out = capsys.readouterr().out
    assert "architectures  plan_execute\n" in out and "not written yet" not in out
    assert "model calls (est.)" in out and "tokens" in out
    assert list(tmp_path.iterdir()) == []
