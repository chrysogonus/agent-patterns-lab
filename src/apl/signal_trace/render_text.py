"""A pipe as text, for `apl signal show` (specs/009 contracts/cli.md)."""

from apl.signal_trace.model import Pipe
from apl.signal_trace.strategy import reference_run


def render_text(pipe: Pipe, route: bool = False) -> str:
    """The header line, one line per run (`  18 → 19–30`) and, with `route`, the reference."""
    name = pipe.level.name if pipe.level else "custom"
    runs = len(pipe.runs)
    best = "optimal" if pipe.reference_is_optimal else "a reference"
    lines = [
        f"Signal trace {name}, seed {pipe.seed}: {pipe.segments} segments, {runs} "
        f"run{'' if runs == 1 else 's'}; broken segment {pipe.broken}; "
        f"reference {pipe.reference_steps} steps ({best}); budget {pipe.budget}"
    ]
    for run in pipe.runs:
        source = "S" if run.feeder == 0 else str(run.feeder)
        span = str(run.first) if run.first == run.last else f"{run.first}–{run.last}"
        lines.append(f"  {source} → {span}")
    if route:
        probes, submitted = reference_run(pipe)
        said = ", ".join(f"{k} {'wet' if water else 'dry'}" for k, water in probes)
        lines.append(
            f"reference: {said} → submit {submitted}" if said else f"reference: submit {submitted}"
        )
    return "\n".join(lines) + "\n"
