"""A floor as text, for `apl rune show` (specs/010 contracts/cli.md). For the experimenter only:
it states the rule."""

from apl.rune.model import COLUMNS, Floor, cell_name
from apl.rune.rules import describe, reference_path

LETTER = {"red": "r", "blue": "b", "green": "g", "yellow": "y", "start": "S", "goal": "*"}


def render_text(floor: Floor, route: bool = False) -> str:
    """The header line, the column letters, one line per row and the legend; with `route`, the
    reference path."""
    name = floor.level.name if floor.level else "custom"
    lines = [
        f"Rune floor {name}, seed {floor.seed}: {floor.columns}×{floor.rows}; "
        f"rule: {describe(floor.rule)}; reference {floor.reference_steps} steps (optimal); "
        f"budget {floor.budget}",
        "    " + " ".join(COLUMNS[: floor.columns]),
    ]
    for y in range(floor.rows):
        cells = " ".join(LETTER[floor.word((x, y))] for x in range(floor.columns))
        lines.append(f"{y + 1:>3} {cells}")
    lines.append("legend: r red, b blue, g green, y yellow, S start, * goal")
    if floor.rule.traps:  # R0: the rule is the trap cells themselves
        lines.append("traps: " + ", ".join(cell_name(c) for c in sorted(floor.rule.traps)))
    if route:
        path = reference_path(floor) or []
        names = " → ".join(cell_name(c) for c in path)
        lines.append(f"reference: {names} ({len(path) - 1} moves)")
    return "\n".join(lines) + "\n"
