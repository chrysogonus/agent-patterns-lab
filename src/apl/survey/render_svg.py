"""A survey field as SVG, for the viewer and `apl survey show --html` (specs/005 R13)."""

from apl.survey.model import COLUMNS, Field, cell_name

CELL = 40
MARGIN = 24


def _line(x1: float, y1: float, x2: float, y2: float) -> str:
    return f'<line class="wall" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'


def svg(field: Field, animated: bool = False) -> str:
    """Cells, deposits, walls and the start. `animated` adds what the viewer moves: the same
    `#fail`, `.room` overlays (fog), `#trail` and `#agent` as the dungeon's picture."""
    n = field.size
    size = 2 * MARGIN + n * CELL
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" role="img" '
        'aria-label="Survey field">'
    ]
    if animated:
        out.append(f'<rect id="fail" x="0" y="0" width="{CELL}" height="{CELL}"/>')
    for col, row in field.all_cells():
        x, y = MARGIN + col * CELL, MARGIN + row * CELL
        out.append(
            f'<rect class="cell" data-cell="{cell_name((col, row))}" '
            f'x="{x}" y="{y}" width="{CELL}" height="{CELL}"/>'
        )
        if (col, row) in field.deposits:
            cx, cy = x + CELL // 2, y + CELL // 2
            points = f"{cx},{cy - 11} {cx + 10},{cy + 8} {cx - 10},{cy + 8}"
            out.append(f'<polygon class="deposit" points="{points}"/>')
    for col in range(n):
        x = MARGIN + col * CELL + CELL // 2
        label = f'<text class="label" x="{x}" y="{MARGIN - 8}" text-anchor="middle">'
        out.append(f"{label}{COLUMNS[col]}</text>")
    for row in range(n):
        y = MARGIN + row * CELL + CELL // 2 + 4
        out.append(
            f'<text class="label" x="{MARGIN - 8}" y="{y}" text-anchor="end">{row + 1}</text>'
        )
    for pair in sorted(field.walls, key=sorted):
        (ax, ay), (bx, by) = sorted(pair)
        if bx > ax:  # a wall east of the first cell
            x = MARGIN + bx * CELL
            out.append(_line(x, MARGIN + ay * CELL, x, MARGIN + (ay + 1) * CELL))
        else:  # a wall south of the first cell
            y = MARGIN + by * CELL
            out.append(_line(MARGIN + ax * CELL, y, MARGIN + (ax + 1) * CELL, y))
    sx, sy = field.start
    out.append(
        f'<rect class="start" x="{MARGIN + sx * CELL + 3}" y="{MARGIN + sy * CELL + 3}" '
        f'width="{CELL - 6}" height="{CELL - 6}"/>'
    )
    out.append(
        f'<rect class="edge" x="{MARGIN}" y="{MARGIN}" width="{n * CELL}" height="{n * CELL}"/>'
    )
    if animated:
        for col, row in field.all_cells():
            out.append(
                f'<rect class="room" id="room-{col}-{row}" x="{MARGIN + col * CELL}" '
                f'y="{MARGIN + row * CELL}" width="{CELL}" height="{CELL}"/>'
            )
        cx, cy = (MARGIN + c * CELL + CELL // 2 for c in field.start)
        out.append('<polyline id="trail" points=""/>')
        out.append(f'<circle id="agent" cx="{cx}" cy="{cy}" r="9"/>')
    out.append("</svg>")
    return "\n".join(out)


def html(field: Field) -> str:
    style = (
        ".cell{fill:#fff;stroke:#e5e3de}.deposit{fill:#ca8a04}.wall,.edge{stroke:#1f2328;"
        "stroke-width:4;fill:none}.start{fill:none;stroke:#7c3aed;stroke-width:2}"
        ".label{font:12px monospace;fill:#6b7280}"
    )
    name = field.level.name if field.level else "custom"
    return (
        f"<!doctype html><meta charset='utf-8'><title>Survey field {name} {field.seed}</title>"
        f"<style>{style}</style>{svg(field)}\n"
    )
