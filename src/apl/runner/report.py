"""Reports built by code from run folders (contracts/results.md "Report", research R13)."""

import json
import statistics
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from apl.runner.results import EpisodeRow, RunRecord

# Runs that differ in any of these are not comparable (Constitution I).
COMPARED = ("model", "temperature", "reasoning_effort", "token_cap", "prompt_fingerprint")


@dataclass(frozen=True, slots=True)
class LoadedRun:
    path: Path
    record: RunRecord
    rows: tuple[EpisodeRow, ...]


def load_run(path: Path) -> LoadedRun:
    run_json = path / "run.json"
    if not run_json.is_file():
        raise ValueError(f"{path} is not a run folder (no run.json)")
    try:
        record = RunRecord.parse(json.loads(run_json.read_text(encoding="utf-8")))
    except ValueError as error:  # includes JSONDecodeError
        raise ValueError(f"{run_json}: {error}") from None
    rows_path = path / "episodes.jsonl"
    rows = []
    lines = rows_path.read_text(encoding="utf-8").splitlines() if rows_path.exists() else []
    for number, line in enumerate(lines, 1):
        try:
            rows.append(EpisodeRow.parse(json.loads(line)))
        except ValueError as error:
            raise ValueError(f"{rows_path}:{number}: {error}") from None
    return LoadedRun(path, record, tuple(rows))


def _distinct(values: Sequence[object]) -> list[str]:
    return list(dict.fromkeys(str(v) for v in values))


def check_compatible(runs: Sequence[LoadedRun]) -> list[str]:
    """Refuses runs that cannot be compared; returns notes on harmless differences."""
    records = [r.record for r in runs]
    differing = []
    for name, values in [("seed_set", [r.seed_set for r in records])] + [
        (f, [r.settings.get(f) for r in records]) for f in COMPARED
    ]:
        if len(distinct := _distinct(values)) > 1:
            differing.append(f"{name} differs ({' vs '.join(distinct)})")
    if differing:
        raise ValueError("cannot combine runs: " + "; ".join(differing))
    notes = []
    if len({r.seeds for r in records}) > 1:
        notes.append("The runs did not all use the same seeds.")
    if len({r.repeats for r in records}) > 1:
        notes.append("The runs did not all use the same number of repeats.")
    return notes


def _median(values: Sequence[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return statistics.median(present) if present else None


def _rate(rows: Sequence[EpisodeRow], test: Callable[[EpisodeRow], bool | None]) -> float:
    return sum(bool(test(r)) for r in rows) / len(rows)


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.0%}"


def _fixed(value: float | None, digits: int, unit: str = "") -> str:
    return "—" if value is None else f"{value:,.{digits}f}{unit}"


def _count(value: float | None) -> str:
    return _fixed(value, 0 if value is None or value == int(value) else 1)


def _stats_row(arch: str, level: str, rows: Sequence[EpisodeRow]) -> str:
    successes = [r.efficiency for r in rows if r.success]
    cells = [
        arch,
        level,
        str(len(rows)),
        _pct(_rate(rows, lambda r: r.success)),
        _fixed(_median(successes), 2),
        _fixed(sum(r.invalid_actions or 0 for r in rows) / len(rows), 1),
        _pct(_rate(rows, lambda r: r.budget_hit)),
        _pct(_rate(rows, lambda r: r.token_cap_hit)),
        _count(_median([r.llm_calls for r in rows])),
        _count(_median([r.input_tokens for r in rows])),
        _count(_median([r.output_tokens for r in rows])),
        _fixed(_median([r.latency_s for r in rows]), 1, "s"),
    ]
    return "| " + " | ".join(cells) + " |"


def _spread_row(arch: str, level: str, rows: Sequence[EpisodeRow]) -> str:
    by_repeat: dict[tuple[str, int], list[EpisodeRow]] = defaultdict(list)
    for row in rows:
        by_repeat[row.run_id, row.repeat].append(row)
    success = [_rate(group, lambda r: r.success) for group in by_repeat.values()]
    efficiency = [
        e
        for group in by_repeat.values()
        if (e := _median([r.efficiency for r in group if r.success])) is not None
    ]
    eff = f"{min(efficiency):.2f}–{max(efficiency):.2f}" if efficiency else "—"
    return f"| {arch} | {level} | {min(success):.0%}–{max(success):.0%} | {eff} |"


_HEADER = (
    "| Arch | Level | Episodes | Success | Efficiency (median) | Invalid / ep | Budget hit "
    "| Token cap hit | Calls (median) | Input tokens (median) | Output tokens (median) "
    "| Latency (median) |"
)


def render(runs: Sequence[LoadedRun]) -> str:
    notes = check_compatible(runs)
    first = runs[0].record
    rows = [row for run in runs for row in run.rows]
    completed = [r for r in rows if r.status == "completed"]
    errors = [r for r in rows if r.status == "error"]
    groups: dict[tuple[str, str], list[EpisodeRow]] = defaultdict(list)
    for row in completed:
        groups[row.arch, row.level].append(row)
    keys = sorted(groups)
    archs = sorted({a for run in runs for a in run.record.architectures})
    settings = first.settings
    lines = [f"# Report: {', '.join(archs)}", ""]
    if first.seed_set == "test":
        lines.append("> Result on test seeds.")
    else:
        lines.append("> Development result (dev seeds). Must not be reported.")
    lines += [
        "",
        f"Runs: {', '.join(r.record.run_id for r in runs)} · model {settings['model']} · "
        f"temperature {settings['temperature']} · reasoning {settings['reasoning_effort']} · "
        f"token cap {settings['token_cap']:,} · prompt {settings['prompt_fingerprint']} · "
        f"seeds {first.seed_set} {', '.join(map(str, first.seeds))} · "
        f"repeats {', '.join(_distinct([r.record.repeats for r in runs]))}",
        "",
        _HEADER,
        "| --- " * 12 + "|",
        *(_stats_row(arch, level, groups[arch, level]) for arch, level in keys),
    ]
    if any(r.record.repeats > 1 for r in runs):
        lines += [
            "",
            "## Spread across repeats",
            "",
            "| Arch | Level | Success (min–max) | Efficiency (min–max) |",
            "| --- | --- | --- | --- |",
            *(_spread_row(arch, level, groups[arch, level]) for arch, level in keys),
        ]
    if errors:
        lines += [
            "",
            "## Infrastructure errors (not scored)",
            "",
            "| Arch | Level | Seed | Repeat | Error |",
            "| --- | --- | --- | --- | --- |",
            *(f"| {r.arch} | {r.level} | {r.seed} | {r.repeat} | {r.error} |" for r in errors),
        ]
    missing = sum(r.input_tokens is None for r in completed)
    if missing:
        notes.append(f"{missing} episode{' has' if missing == 1 else 's have'} no token data.")
    notes += [f"Run {r.record.run_id} is incomplete." for r in runs if not r.record.completed]
    if notes:
        lines += ["", "Notes: " + " ".join(notes)]
    return "\n".join(lines) + "\n"
