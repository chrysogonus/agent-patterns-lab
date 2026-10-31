"""The report's comparison section: architectures side by side per level (specs/004 R14).

Each architecture is compared with the one that differs from it in one job, its reference.
"""

from collections import defaultdict
from collections.abc import Sequence

from apl.runner.report import LoadedRun, _count, _distinct, _fixed, _median, _pct, _rate
from apl.runner.results import EpisodeRow

REFERENCES = {
    "mapstate": "react",
    "mapstate_routes": "mapstate",
    "hybrid": "mapstate_routes",
    "fanout": "mapstate",
    "rounds": "mapstate",
    "blackboard": "mapstate",
}

_HEADER = (
    "| Arch | Success | Efficiency | Steps | Tokens | Calls: orch / scouts | Latency | Scouts "
    "| Δ success | Δ efficiency | Reference |"
)


def _signed(value: float, digits: int, unit: str = "") -> str:
    return f"{value:+.{digits}f}{unit}".replace("-", "−")


def _efficiency(rows: Sequence[EpisodeRow]) -> float | None:
    return _median([r.efficiency for r in rows if r.success])


def _tokens(row: EpisodeRow) -> int | None:
    if row.input_tokens is None or row.output_tokens is None:
        return None
    return row.input_tokens + row.output_tokens


def _row(arch: str, rows: Sequence[EpisodeRow], reference: Sequence[EpisodeRow] | None) -> str:
    success = _rate(rows, lambda r: r.success)
    efficiency = _efficiency(rows)
    known = [r for r in rows if r.orchestrator_calls is not None]
    orchestrator = _median([r.orchestrator_calls for r in known]) if known else None
    scouts_calls = (
        _median([r.llm_calls - (r.orchestrator_calls or 0) for r in known]) if known else None
    )
    d_success = d_efficiency = "—"
    if reference:
        d_success = _signed(100 * (success - _rate(reference, lambda r: r.success)), 0, " pp")
        ref_efficiency = _efficiency(reference)
        if efficiency is not None and ref_efficiency is not None:
            d_efficiency = _signed(efficiency - ref_efficiency, 2)
    cells = [
        arch,
        _pct(success),
        _fixed(efficiency, 2),
        _count(_median([r.steps for r in rows])),
        _count(_median([_tokens(r) for r in rows])),
        f"{_count(orchestrator)} / {_count(scouts_calls)}",
        _fixed(_median([r.latency_s for r in rows]), 1, "s"),
        _count(_median([r.scouts for r in rows])),
        d_success,
        d_efficiency,
        REFERENCES.get(arch, "—"),
    ]
    return "| " + " | ".join(cells) + " |"


def render_comparison(runs: Sequence[LoadedRun], completed: Sequence[EpisodeRow]) -> list[str]:
    """The section's lines; empty when the rows cover fewer than two architectures."""
    groups: dict[tuple[str, str], list[EpisodeRow]] = defaultdict(list)
    for row in completed:
        groups[row.level, row.arch].append(row)
    present = {arch for _, arch in groups}
    if len(present) < 2:
        return []
    first = runs[0].record
    order = [a for a in first.architectures if a in present]
    order += sorted(present - set(order))
    seeds = ", ".join(map(str, sorted({r.seed for r in completed})))
    repeats = ", ".join(_distinct([r.record.repeats for r in runs]))
    plural = "" if repeats == "1" else "s"
    notice = (
        "> Result on test seeds."
        if first.seed_set == "test"
        else "> Development result (dev seeds). Must not be reported."
    )
    lines = [
        "",
        "## Comparison",
        "",
        notice,
        "",
        f"Seeds {seeds}, {repeats} repeat{plural}. Differences are against the reference "
        "architecture in the last column.",
    ]
    for level in sorted({level for level, _ in groups}):
        lines += ["", f"### {level}", "", _HEADER, "| --- " * 11 + "|"]
        for arch in order:
            if (level, arch) in groups:
                reference = groups.get((level, REFERENCES.get(arch, "")))
                lines.append(_row(arch, groups[level, arch], reference))
    return lines
