"""A warehouse floor as SVG, for the viewer and `apl warehouse show --html` (specs/012 R14)."""

from apl.warehouse.model import COLUMNS, Floor, cell_name

CELL = 40
MARGIN = 24
PACKAGE = 18  # a package's side; the page moves it to its cell or robot


def svg(floor: Floor, animated: bool = False) -> str:
    """Shelves, open cells with their `.room` overlays (the fog), the dock, D and the packages.
    `animated` adds what the viewer moves: `#fail`, `#trail` and `#agent`."""
    width, height = 2 * MARGIN + floor.columns * CELL, 2 * MARGIN + floor.rows * CELL
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Warehouse">'
    ]
    if animated:
        out.append(f'<rect id="fail" x="0" y="0" width="{CELL}" height="{CELL}"/>')
    cells = [(x, y) for y in range(floor.rows) for x in range(floor.columns)]
    for x, y in cells:
        kind = "shelf" if floor.shelf((x, y)) else "cell"
        out.append(
            f'<rect class="{kind}" data-cell="{cell_name((x, y))}" x="{MARGIN + x * CELL}" '
            f'y="{MARGIN + y * CELL}" width="{CELL}" height="{CELL}"/>'
        )
    for col in range(floor.columns):
        x = MARGIN + col * CELL + CELL // 2
        out.append(f'<text class="label" x="{x}" y="{MARGIN - 8}" text-anchor="middle">'
                   f"{COLUMNS[col]}</text>")  # fmt: skip
    for row in range(floor.rows):
        y = MARGIN + row * CELL + CELL // 2 + 4
        out.append(
            f'<text class="label" x="{MARGIN - 8}" y="{y}" text-anchor="end">{row + 1}</text>'
        )
    for (x, y), mark in ((floor.dock, "S"), (floor.drop, "D")):
        cx, cy = MARGIN + x * CELL + CELL // 2, MARGIN + y * CELL + CELL // 2 + 6
        out.append(f'<text class="marker" x="{cx}" y="{cy}" text-anchor="middle">{mark}</text>')
    dx, dy = floor.drop
    out.append(
        f'<rect id="exit" x="{MARGIN + dx * CELL + 3}" y="{MARGIN + dy * CELL + 3}" '
        f'width="{CELL - 6}" height="{CELL - 6}"/>'
    )
    for name, (x, y) in sorted(floor.packages):
        offset = (CELL - PACKAGE) // 2
        out.append(
            f'<rect class="package" data-package="{name}" x="{MARGIN + x * CELL + offset}" '
            f'y="{MARGIN + y * CELL + offset}" width="{PACKAGE}" height="{PACKAGE}" rx="3"/>'
        )
    for x, y in cells:
        if floor.open((x, y)):
            out.append(
                f'<rect class="room" id="room-{x}-{y}" x="{MARGIN + x * CELL}" '
                f'y="{MARGIN + y * CELL}" width="{CELL}" height="{CELL}"/>'
            )
    if animated:
        cx, cy = (MARGIN + c * CELL + CELL // 2 for c in floor.dock)
        out.append('<polyline id="trail" points=""/>')
        out.append(f'<circle id="agent" cx="{cx}" cy="{cy}" r="9"/>')
    out.append("</svg>")
    return "\n".join(out)


def html(floor: Floor) -> str:
    style = (
        ".cell{fill:#fff;stroke:#e5e3de}.shelf{fill:#1f2328}.room{fill:none}"
        ".package{fill:#ca8a04}#exit{fill:none;stroke:#16a34a;stroke-width:3;"
        "stroke-dasharray:6 4}.marker{font:bold 16px monospace}"
        ".label{font:12px monospace;fill:#6b7280}"
    )
    name = floor.level.name if floor.level else "custom"
    return (
        f"<!doctype html><meta charset='utf-8'><title>Warehouse {name} {floor.seed}</title>"
        f"<style>{style}</style>{svg(floor)}\n"
    )
