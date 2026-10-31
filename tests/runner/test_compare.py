"""The comparison section of the report, from hand-written rows (specs/004 SC-005)."""

import random
from pathlib import Path
from typing import Any

from apl.runner.report import load_run, render
from tests.runner.test_report import _row, _write

ARCHS = ["react", "mapstate", "mapstate_routes", "hybrid", "fanout", "rounds", "blackboard"]


def _ep(arch: str, level: str, steps: int, success: bool, **kw: Any) -> dict[str, Any]:
    row = _row(1000, 1, steps, arch=arch, level=level, success=success,
               end_reason="exit" if success else "stopped", **kw)  # fmt: skip
    return row


def _rows() -> list[dict[str, Any]]:
    # optimal_steps is 8 in every row: efficiency 8 / steps on success.
    return [
        _ep("react", "L1", 10, True, input_tokens=100, output_tokens=20, llm_calls=5,
            orchestrator_calls=0, scouts=1, latency_s=2.0),
        _ep("mapstate", "L1", 8, True, input_tokens=50, output_tokens=10, llm_calls=4,
            orchestrator_calls=0, scouts=1, latency_s=1.0),
        _ep("fanout", "L1", 20, False, input_tokens=300, output_tokens=30, llm_calls=9,
            orchestrator_calls=1, scouts=3, latency_s=5.5),
        _ep("react", "L2", 24, False, input_tokens=10, output_tokens=0, llm_calls=1,
            orchestrator_calls=0, scouts=1, latency_s=1.0),
        _ep("fanout", "L2", 20, True, input_tokens=1000, output_tokens=234, llm_calls=12,
            orchestrator_calls=1, scouts=4, latency_s=12.25),
    ]  # fmt: skip


def _report(tmp_path: Path, rows: list[dict[str, Any]], name: str = "run-a") -> str:
    path = _write(tmp_path / name, rows, architectures=ARCHS, levels=["L1", "L2"], seeds=[1000],
                  repeats=1)  # fmt: skip
    return render([load_run(path)])


EXPECTED = """\
## Comparison

> Development result (dev seeds). Must not be reported.

Seeds 1000, 1 repeat. Differences are against the reference architecture in the last column.

### L1

| Arch | Success | Efficiency | Steps | Tokens | Calls: orch / scouts | Latency | Scouts | Δ success | Δ efficiency | Reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| react | 100% | 0.80 | 10 | 120 | 0 / 5 | 2.0s | 1 | — | — | — |
| mapstate | 100% | 1.00 | 8 | 60 | 0 / 4 | 1.0s | 1 | +0 pp | +0.20 | react |
| fanout | 0% | — | 20 | 330 | 1 / 8 | 5.5s | 3 | −100 pp | — | mapstate |

### L2

| Arch | Success | Efficiency | Steps | Tokens | Calls: orch / scouts | Latency | Scouts | Δ success | Δ efficiency | Reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| react | 0% | — | 24 | 10 | 0 / 1 | 1.0s | 1 | — | — | — |
| fanout | 100% | 0.40 | 20 | 1,234 | 1 / 11 | 12.2s | 4 | — | — | mapstate |
"""  # noqa: E501


def test_every_cell_matches_the_hand_calculation(tmp_path: Path) -> None:
    report = _report(tmp_path, _rows())
    section = report[report.index("## Comparison") :]
    assert section.split("\n\nNotes:")[0].rstrip() + "\n" == EXPECTED


def test_the_order_of_rows_does_not_matter(tmp_path: Path) -> None:
    rows = _rows()
    shuffled = random.Random(4).sample(rows, len(rows))
    assert _report(tmp_path / "1", rows) == _report(tmp_path / "2", shuffled)


def test_rows_from_before_m4_show_dashes(tmp_path: Path) -> None:
    rows = [_ep("react", "L1", 10, True), _ep("mapstate", "L1", 8, True)]  # no scouts fields
    for row in rows:
        row.pop("orchestrator_calls", None), row.pop("scouts", None)
    report = _report(tmp_path, rows)
    assert "| mapstate | 100% | 1.00 | 8 | 0 | — / — | 1.0s | — | +0 pp | +0.20 | react |" in report


def test_one_architecture_has_no_comparison(tmp_path: Path) -> None:
    rows = [r for r in _rows() if r["arch"] == "react"]
    assert "## Comparison" not in _report(tmp_path, rows)
