"""A pipe as SVG, for the viewer and `apl signal show --html` (specs/009 research R13).

Drawn as in the problem mock-up: each run snakes `PER_ROW` segments a row (left to right, then
back), with a grey pipe line through the segment centres. Runs are stacked one under another, and
each starts at an inlet left of its first segment, labelled "S" or "from 18", so no line crosses
the board. Boxes carry `data-seg`, and
the page draws the water, the probe marks and the suspects from the frames (`#water`, `#probes`).
"""

from apl.signal_trace.model import Pipe

CELL = 26  # a box
PER_ROW = 8
LABEL = 64  # the column for "S" and "from 18"
MARGIN = 14
BLOCK_GAP = 14  # between runs


def layout(pipe: Pipe) -> dict[int, tuple[int, int]]:
    """Each segment's box position (x, y): runs stacked, each snaking PER_ROW a row."""
    places: dict[int, tuple[int, int]] = {}
    top = MARGIN
    for run in pipe.runs:
        segments = range(run.first, run.last + 1)
        for i, k in enumerate(segments):
            row, col = divmod(i, PER_ROW)
            col = col if row % 2 == 0 else PER_ROW - 1 - col
            places[k] = (MARGIN + LABEL + col * CELL, top + row * CELL)
        rows = -(-len(segments) // PER_ROW)
        top += rows * CELL + BLOCK_GAP
    return places


def _centre(place: tuple[int, int]) -> tuple[int, int]:
    return place[0] + CELL // 2, place[1] + CELL // 2


def inlet(places: dict[int, tuple[int, int]], first: int) -> tuple[int, int]:
    """Where a run's pipe comes in: one box left of its first segment."""
    x, y = _centre(places[first])
    return x - CELL, y


def svg(pipe: Pipe, animated: bool = False) -> str:
    """The boxes, the pipe line, run labels and a ring on the broken segment (`class="broken"`).
    `animated` adds an id to the ring (hidden under "Agent's view") and the empty groups the page
    fills: `#water` and `#probes`."""
    places = layout(pipe)
    sx, sy = inlet(places, 1)
    width = 2 * MARGIN + LABEL + PER_ROW * CELL
    height = max(y for _, y in places.values()) + CELL + MARGIN
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Signal trace pipe">'
    ]
    for k, (x, y) in sorted(places.items()):
        out.append(
            f'<rect class="seg" data-seg="{k}" x="{x + 1}" y="{y + 1}" width="{CELL - 2}" '
            f'height="{CELL - 2}" rx="3"/>'
        )
    for run in pipe.runs:
        ix, iy = inlet(places, run.first)
        points = [(ix, iy), *(_centre(places[k]) for k in range(run.first, run.last + 1))]
        line = " ".join(f"{x},{y}" for x, y in points)
        out.append(f'<polyline class="pipe" points="{line}"/>')
        if run.feeder:
            out.append(f'<circle class="inlet" cx="{ix}" cy="{iy}" r="3"/>')
            out.append(
                f'<text class="label" x="{ix - 6}" y="{iy + 4}" '
                f'text-anchor="end">from {run.feeder}</text>'
            )
    out.append(f'<circle class="source-dot" cx="{sx}" cy="{sy}" r="3"/>')
    out.append(f'<text class="label source" x="{sx - 6}" y="{sy + 5}" text-anchor="end">S</text>')
    for k, (x, y) in sorted(places.items()):
        out.append(f'<text class="seg-label" x="{x + 3}" y="{y + 9}">{k}</text>')
    if animated:
        out.append('<g id="water"></g><g id="probes"></g>')
    bx, by = places[pipe.broken]
    ident = ' id="broken"' if animated else ""
    out.append(
        f'<rect class="broken"{ident} x="{bx - 1}" y="{by - 1}" width="{CELL + 2}" '
        f'height="{CELL + 2}" rx="4"/>'
    )
    out.append("</svg>")
    return "\n".join(out)


def html(pipe: Pipe) -> str:
    style = (
        ".seg{fill:#fff;stroke:#e5e3de}.pipe{fill:none;stroke:#6b7280;stroke-width:3;"
        "stroke-opacity:.45;stroke-linejoin:round}.seg-label{font:7px monospace;fill:#9ca3af}"
        ".broken{fill:none;stroke:#dc2626;stroke-width:2;stroke-dasharray:3 2}"
        ".label{font:12px monospace;fill:#6b7280}.source{font-weight:700;fill:#1f2328}"
        ".source-dot{fill:#0891b2}.inlet{fill:#6b7280}"
    )
    name = pipe.level.name if pipe.level else "custom"
    return (
        f"<!doctype html><meta charset='utf-8'><title>Signal trace {name} {pipe.seed}</title>"
        f"<style>{style}</style>{svg(pipe)}\n"
    )
