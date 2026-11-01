"""A survey field as a text picture, for `apl survey show` (specs/005 contracts/cli.md)."""

from apl.survey.model import COLUMNS, Cell, Field, wall


def _visits(field: Field) -> dict[Cell, int]:
    """Each cell's number in the order the reference walk first enters it, from 1."""
    order, here = {field.start: 1}, field.start
    for direction in field.walk:
        nxt = field.neighbor(here, direction)
        assert nxt is not None
        here = nxt
        order.setdefault(here, len(order) + 1)
    return order


def render_text(field: Field, route: bool = False) -> str:
    """Cells are three characters wide: `S` start, `o` deposit, `.` empty; walls `|` and `—`.

    With `route`, each cell shows its number in the reference walk, then `o` for a deposit.
    """
    n = field.size
    name = field.level.name if field.level else "custom"
    shortest = "shortest" if field.reference_is_optimal else "a reference, not the shortest"
    lines = [
        f"Survey field {name}, seed {field.seed}: {n}×{n}, {field.true_total} deposits; "
        f"reference walk {field.reference_steps} steps ({shortest}); budget {field.budget}",
        ("    " + " ".join(f" {c} " for c in COLUMNS[:n])).rstrip(),
    ]
    visits = _visits(field) if route else {}
    for row in range(n):
        cells = []
        for col in range(n):
            cell = (col, row)
            mark = "o" if cell in field.deposits else ("S" if cell == field.start else ".")
            text = (
                f"{visits[cell]:>2}{'o' if cell in field.deposits else ' '}"
                if route
                else f" {mark} "
            )
            east = wall(cell, (col + 1, row)) in field.walls
            cells.append(text + ("|" if east else " "))
        lines.append(f"{row + 1:>2}  " + "".join(cells).rstrip())
        under = "".join(
            ("—" * 3 if wall((col, row), (col, row + 1)) in field.walls else "   ") + " "
            for col in range(n)
        )
        lines.append(("    " + under).rstrip())
    return "\n".join(lines) + "\n"
