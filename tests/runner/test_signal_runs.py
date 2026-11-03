"""Signal-trace runs: plan, interrupt, continue, rows (specs/009 US3, contracts/results.md)."""

import json
from pathlib import Path

import pytest

from apl.runner import registry, run
from apl.runner.run import continue_run, execute, plan_continue
from apl.runner.settings import Settings
from apl.runner.spec import RunSpec
from apl.signal_trace import generate
from tests.runner.scripted import (
    FakeProviderError,
    raise_error,
    scripted_factory,
    text_answer,
    then,
)
from tests.runner.test_continue import CODE

ARCHS = ["react", "mapstate"]
SIGNAL_FIELDS = (
    "submitted_segment", "broken_segment", "segments", "probes", "wasted_probes",
    "reference_is_optimal",
)  # fmt: skip


@pytest.fixture(autouse=True)
def _clean_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, "code_version", lambda: dict(CODE))


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in (path / "episodes.jsonl").read_text().splitlines()]


def test_an_interrupted_signal_run_continues(tmp_path: Path) -> None:  # US3 3
    plays = {name: registry.load(name) for name in ARCHS}
    spec = RunSpec.build(ARCHS, ["T1"], "dev", limit=2, problem="signal")
    first = execute(
        spec, Settings(), results_dir=tmp_path, architectures=plays,
        model_factory=scripted_factory(then(text_answer(), 2, raise_error(KeyboardInterrupt()))),
    )  # fmt: skip
    assert first.exit_code == 130
    assert json.loads((first.path / "run.json").read_text())["problem"] == "signal"
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
    assert sorted((r["arch"], r["seed"]) for r in rows) == sorted(
        (a, s) for a in ARCHS for s in spec.seeds
    )
    for row in rows:
        pipe = generate("T1", int(str(row["seed"])))
        assert row["problem"] == "signal" and all(f in row for f in SIGNAL_FIELDS)
        assert row["broken_segment"] == pipe.broken and row["segments"] == 16
        assert row["submitted_segment"] is None and row["probes"] == 0
        assert row["wasted_probes"] == 0 and row["reference_is_optimal"] is True


def test_an_infrastructure_error_still_records_the_pipe(tmp_path: Path) -> None:
    spec = RunSpec.build(["react"], ["T2"], "dev", limit=1, problem="signal")
    outcome = execute(
        spec, Settings(), results_dir=tmp_path, architectures={"react": registry.load("react")},
        model_factory=scripted_factory(raise_error(FakeProviderError(429))),
    )  # fmt: skip
    (row,) = _rows(outcome.path)
    assert row["status"] == "error" and row["problem"] == "signal"
    assert row["broken_segment"] == generate("T2", 1000).broken and row["segments"] == 64
    assert row["optimal_steps"] == 7 and row["budget"] == 64
