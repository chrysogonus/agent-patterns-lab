"""A floor as SVG, for the viewer and `apl rune show --html` (specs/010 research R14).

Drawn as in the problem mock-up: one tile per cell in a soft fill of its color, S and G labelled,
column letters and row numbers around the board. The rule is written above it and the reference
path outlined; the page hides both under "Agent's view" and draws the trails, traps and the agent
from the frames (`#trails`, `#traps`, `#agent`).
"""

from apl.rune.model import COLUMNS, Cell, Floor, cell_name
from apl.rune.rules import describe, reference_path

CELL = 34
MARGIN = 14
AXIS = 18  # the column of row numbers and the row of column letters
TOP = 22  # the line for the rule


def origin(floor: Floor) -> tuple[int, int]:
    return MARGIN + AXIS, MARGIN + TOP + AXIS


def centre(floor: Floor, cell: Cell) -> tuple[int, int]:
    ox, oy = origin(floor)
    return ox + cell[0] * CELL + CELL // 2, oy + cell[1] * CELL + CELL // 2


def svg(floor: Floor, animated: bool = False) -> str:
    """The tiles, S and G, the axis labels, the rule (`class="rule"`) and the reference path
    (`class="reference"`). `animated` adds ids to the rule and the path (hidden under "Agent's
    view") and the empty groups the page fills."""
    ox, oy = origin(floor)
    width = ox + floor.columns * CELL + MARGIN
    height = oy + floor.rows * CELL + MARGIN
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Rune floor">'
    ]
    ident = ' id="rule"' if animated else ""
    out.append(
        f'<text class="rule"{ident} x="{ox}" y="{MARGIN + 14}">rule: {describe(floor.rule)}</text>'
    )
    for x in range(floor.columns):
        cx = ox + x * CELL + CELL // 2
        out.append(
            f'<text class="axis" x="{cx}" y="{oy - 6}" text-anchor="middle">{COLUMNS[x]}</text>'
        )
    for y in range(floor.rows):
        cy = oy + y * CELL + CELL // 2 + 4
        out.append(f'<text class="axis" x="{ox - 6}" y="{cy}" text-anchor="end">{y + 1}</text>')
    for y in range(floor.rows):
        for x in range(floor.columns):
            word, name = floor.word((x, y)), cell_name((x, y))
            out.append(
                f'<rect class="tile {word}" data-cell="{name}" x="{ox + x * CELL + 1}" '
                f'y="{oy + y * CELL + 1}" width="{CELL - 2}" height="{CELL - 2}" rx="4"/>'
            )
    for cell, label in ((floor.start, "S"), (floor.goal, "G")):
        cx, cy = centre(floor, cell)
        out.append(f'<text class="mark" x="{cx}" y="{cy + 5}" text-anchor="middle">{label}</text>')
    ident = ' id="truth-traps"' if animated else ""
    marks = []
    for cell in sorted(floor.rule.traps):  # R0's rule is its trap cells
        cx, cy = centre(floor, cell)
        marks.append(f"M{cx - 6} {cy - 6}L{cx + 6} {cy + 6}M{cx + 6} {cy - 6}L{cx - 6} {cy + 6}")
    out.append(f'<path class="truth-traps"{ident} d="{"".join(marks)}"/>')
    path = reference_path(floor) or []
    points = " ".join(f"{x},{y}" for x, y in (centre(floor, c) for c in path))
    ident = ' id="reference"' if animated else ""
    out.append(f'<polyline class="reference"{ident} points="{points}"/>')
    if animated:
        out.append('<g id="trails"></g><g id="traps"></g><g id="agent"></g>')
    out.append("</svg>")
    return "\n".join(out)


def html(floor: Floor) -> str:
    style = (
        ".tile{stroke:#fff;stroke-width:1}.tile.red{fill:#fca5a5}.tile.blue{fill:#93c5fd}"
        ".tile.green{fill:#86efac}.tile.yellow{fill:#fde68a}.tile.start,.tile.goal{fill:#f3f4f6;"
        "stroke:#9ca3af}.mark{font:600 14px monospace;fill:#1f2328}.axis{font:11px monospace;"
        "fill:#6b7280}.rule{font:9px monospace;fill:#1f2328}.reference{fill:none;stroke:#7c3aed;"
        "stroke-width:2;stroke-dasharray:5 4;stroke-linejoin:round}"
        ".truth-traps{fill:none;stroke:#6b7280;stroke-width:1.5;stroke-opacity:.6}"
    )
    name = floor.level.name if floor.level else "custom"
    return (
        f"<!doctype html><meta charset='utf-8'><title>Rune floor {name} {floor.seed}</title>"
        f"<style>{style}</style>{svg(floor)}\n"
    )
