"""A warehouse as text, for `apl warehouse show` (specs/012 contracts/cli.md)."""

from apl.warehouse.model import COLUMNS, Floor


def render_text(floor: Floor, route: bool = False) -> str:
    name = floor.level.name if floor.level else "custom"
    best = "optimal" if floor.reference_is_optimal else "not optimal"
    lines = [
        f"Warehouse {name}, seed {floor.seed}: {len(floor.packages)} packages; "
        f"reference {floor.reference_steps} steps ({best}); budget {floor.budget}",
        "   " + " ".join(COLUMNS[: floor.columns]),
    ]
    at = {cell: n.removeprefix("package ") for n, cell in floor.packages}
    plan = floor.plan()
    for y in range(floor.rows):
        marks = [at.get((x, y), plan[y][x]) for x in range(floor.columns)]
        lines.append(f"{y + 1:<2} " + " ".join(marks))
    counts = []
    for aisle in floor.aisle_names:
        cells = set(floor.corridor_cells(aisle))
        n = sum(1 for _, c in floor.packages if c in cells)
        held = "none" if n == 0 else f"{n} package{'s' if n > 1 else ''}"
        counts.append(f"{aisle} (row {2 * int(aisle.removeprefix('aisle ')) - 1}): {held}")
    lines.append("aisles: " + "; ".join(counts))
    if route:
        lines.append("reference: " + ", ".join(str(a) for a in floor.reference))
    return "\n".join(lines) + "\n"
