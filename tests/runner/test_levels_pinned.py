"""The signal trace's and the workshop's levels, pinned before T4 and W4 (specs/013 T002).

`GOLDEN_REGEN=1` rewrites the expected file, only for a deliberate change of this output.
"""

import dataclasses
import hashlib
import json
import os
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from apl import signal_trace, workshop
from apl.runner import registry, run
from apl.runner.report import load_run, render
from apl.runner.settings import Settings
from apl.runner.spec import RunSpec
from apl.signal_trace import render_svg as signal_svg
from apl.workshop import render_svg as workshop_svg
from tests.runner.scripted import raise_error, scripted_factory, text_answer, then

FIXTURES = Path(__file__).parent / "fixtures"
PINNED = FIXTURES / "levels-pinned.json"
CODE = {"commit": "abc1234", "dirty": False}
SIGNAL_LEVELS = ["T1", "T2", "T3"]  # never LEVELS: these are the levels shipped before specs/013
WORKSHOP_LEVELS = ["W1", "W2", "W3"]


def _hash(value: object) -> str:
    text = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _pipe(level: str, seed: int) -> str:
    pipe = signal_trace.generate(level, seed)
    data = {
        "feeder": pipe.feeder,
        "runs": [dataclasses.astuple(run) for run in pipe.runs],
        "broken": pipe.broken,
        "reference_probes": pipe.reference_probes,
        "budget": pipe.budget,
        "svg": signal_svg.svg(pipe),
    }
    return _hash(data)


def _workshop(level: str, seed: int) -> str:
    w = workshop.generate(level, seed)
    data = {
        "goal": w.goal,
        "recipes": {item: list(recipes) for item, recipes in w.recipes.items()},
        "stock": dict(w.stock),
        "scarce": sorted(w.scarce),
        "reference_choice": dict(w.reference_choice),
        "reference": w.reference,
        "budget": w.budget,
        "svg": workshop_svg.svg(w),
    }
    return _hash(data)


def _current() -> dict[str, str]:
    out = {}
    for level in SIGNAL_LEVELS:
        for seed in [*signal_trace.DEV_SEEDS, *signal_trace.TEST_SEEDS]:
            out[f"signal:{level}:{seed}"] = _pipe(level, seed)
    for level in WORKSHOP_LEVELS:
        for seed in [*workshop.DEV_SEEDS, *workshop.TEST_SEEDS]:
            out[f"workshop:{level}:{seed}"] = _workshop(level, seed)
    return out


def test_the_existing_levels_are_unchanged() -> None:  # FR-008, SC-003
    current = _current()
    if os.environ.get("GOLDEN_REGEN"):
        PINNED.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    assert len(current) == 180
    assert current == json.loads(PINNED.read_text(encoding="utf-8"))


# ---------- the new levels in runs, continue and report (specs/013 US3) ----------


def test_all_now_includes_the_new_level_last() -> None:  # FR-009, SC-004
    signal = RunSpec.build(["react"], ["all"], "dev", limit=1, problem="signal")
    tree = RunSpec.build(["react"], ["all"], "dev", limit=1, problem="workshop")
    assert signal.levels == ("T1", "T2", "T3", "T4")
    assert tree.levels == ("W1", "W2", "W3", "W4")
    assert RunSpec.build(["react"], ["T4"], "dev", limit=1, problem="signal").levels == ("T4",)
    assert RunSpec.build(["react"], ["W4"], "dev", limit=1, problem="workshop").levels == ("W4",)
    budgets = [signal_trace.generate(level, 1000).budget for level in signal.levels]
    assert signal.upper_bounds(Settings()).calls == sum(budgets) + 4 and budgets[-1] == 256
    w4 = workshop.generate("W4", 1000)
    budgets = [workshop.generate(level, 1000).budget for level in tree.levels]
    assert (
        tree.upper_bounds(Settings()).calls == sum(budgets) + 4 and budgets[-1] == 3 * w4.reference
    )


def test_a_three_level_run_continues_without_the_new_level(  # FR-010, SC-004
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run, "code_version", lambda: dict(CODE))
    spec = RunSpec.build(["react"], SIGNAL_LEVELS, "dev", limit=1, problem="signal")
    plays = {"react": registry.load("react")}
    stopped = then(text_answer(), 1, raise_error(KeyboardInterrupt()))
    first = run.execute(
        spec, Settings(), model_factory=scripted_factory(stopped), architectures=plays,
        results_dir=tmp_path,
    )  # fmt: skip
    assert first.exit_code == 130
    plan = run.plan_continue(
        first.path, Settings(), code=CODE, versions=run.package_versions(),
        written={"react": True},
    )  # fmt: skip
    assert not plan.refusals
    assert [k.level for k in plan.left] == ["T2", "T3"] and len(plan.done) == 1


def test_a_run_with_t4_reports_its_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, "code_version", lambda: dict(CODE))  # FR-013
    names = ["react", "hybrid"]  # two, so the report has a comparison section per level
    spec = RunSpec.build(names, ["T3", "T4"], "dev", limit=1, problem="signal")
    outcome = run.execute(
        spec, Settings(), model_factory=scripted_factory(lambda messages: AIMessage("1")),
        architectures={name: registry.load(name) for name in names}, results_dir=tmp_path,
    )  # fmt: skip
    assert outcome.exit_code == 0
    text = render([load_run(outcome.path)])
    assert "| hybrid | T4 | 1 | 100% |" in text and "### T4" in text
