"""A pipe as SVG, for the viewer and `apl signal show --html` (specs/009 research R13).

Each run is a row of segment boxes (wrapped at `PER_ROW`), labelled with what feeds it. Boxes
carry `data-seg`, so the viewer's page can mark them wet, dry, suspect or cleared.
"""

from apl.signal_trace.model import Pipe

CELL = 30  # a box
GAP = 4
PER_ROW = 16
LABEL = 64  # the "18 →" column
MARGIN = 16


def layout(pipe: Pipe) -> dict[int, tuple[int, int]]:
    """Each segment's box position (x, y), and the rows it takes."""
    places, row = {}, 0
    for run in pipe.runs:
        for i, k in enumerate(range(run.first, run.last + 1)):
            if i and i % PER_ROW == 0:
                row += 1
            places[k] = (MARGIN + LABEL + (i % PER_ROW) * (CELL + GAP), MARGIN + row * (CELL + GAP))
        row += 1
    return places


def svg(pipe: Pipe, animated: bool = False) -> str:
    """The boxes, run labels and a ring on the broken segment (`class="broken"`). `animated`
    adds an id to the ring, so the page can hide it under "Agent's view"."""
    places = layout(pipe)
    width = 2 * MARGIN + LABEL + PER_ROW * (CELL + GAP)
    height = 2 * MARGIN + max(y for _, y in places.values()) - MARGIN + CELL
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Signal trace pipe">'
    ]
    for run in pipe.runs:
        x, y = places[run.first]
        source = "S" if run.feeder == 0 else str(run.feeder)
        out.append(
            f'<text class="label" x="{x - 8}" y="{y + CELL // 2 + 4}" text-anchor="end">'
            f"{source} →</text>"
        )
    for k, (x, y) in sorted(places.items()):
        out.append(
            f'<rect class="seg" data-seg="{k}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
            'rx="4"/>'
        )
        out.append(
            f'<text class="seg-label" x="{x + CELL // 2}" y="{y + CELL // 2 + 4}" '
            f'text-anchor="middle">{k}</text>'
        )
    bx, by = places[pipe.broken]
    ident = ' id="broken"' if animated else ""
    out.append(
        f'<rect class="broken"{ident} x="{bx - 3}" y="{by - 3}" width="{CELL + 6}" '
        f'height="{CELL + 6}" rx="6"/>'
    )
    out.append("</svg>")
    return "\n".join(out)


def html(pipe: Pipe) -> str:
    style = (
        ".seg{fill:#fff;stroke:#c9c6bf}.seg-label{font:11px monospace;fill:#1f2328}"
        ".broken{fill:none;stroke:#dc2626;stroke-width:2.5}.label{font:12px monospace;fill:#6b7280}"
    )
    name = pipe.level.name if pipe.level else "custom"
    return (
        f"<!doctype html><meta charset='utf-8'><title>Signal trace {name} {pipe.seed}</title>"
        f"<style>{style}</style>{svg(pipe)}\n"
    )
