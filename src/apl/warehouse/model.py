"""The warehouse's data types (specs/012 data-model.md). Runner side only."""

from __future__ import annotations

from dataclasses import dataclass

Cell = tuple[int, int]  # (column, row); (0, 0) is A1, the north-west corner

COLUMNS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIRECTIONS = ("north", "east", "south", "west")
STEP: dict[str, Cell] = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}
WEST, EAST = "west corridor", "east corridor"


def cell_name(cell: Cell) -> str:
    return COLUMNS[cell[0]] + str(cell[1] + 1)


def parse_cell(name: str) -> Cell:
    return COLUMNS.index(name[0]), int(name[1:]) - 1


@dataclass(frozen=True, slots=True)
class WarehouseLevel:
    name: str
    columns: int
    aisles: int
    spreads: tuple[tuple[int, ...], ...]  # the allowed packages per aisle; one is drawn, shuffled


LEVELS: dict[str, WarehouseLevel] = {
    "P1": WarehouseLevel("P1", columns=9, aisles=3, spreads=((1, 1, 1),)),
    "P2": WarehouseLevel("P2", columns=9, aisles=3, spreads=((0, 1, 2),)),
    "P3": WarehouseLevel("P3", columns=11, aisles=5, spreads=((3, 1, 1, 1, 0), (3, 2, 1, 0, 0))),
}


@dataclass(frozen=True, slots=True)
class Action:
    tool: str  # look, move, pick, drop, or unknown
    args: tuple[str, ...] = ()

    def __str__(self) -> str:
        return " ".join((self.tool, *self.args))

    def to_dict(self) -> dict[str, object]:
        return {"tool": self.tool, "args": list(self.args)}


@dataclass(frozen=True, slots=True)
class Floor:
    """Aisles on the even rows, single shelf rows between them, a corridor at each end (R2)."""

    level: WarehouseLevel | None  # None for a hand-built floor
    seed: int | None
    columns: int
    aisles: int
    packages: tuple[tuple[str, Cell], ...]  # name and cell, in the generator's shuffled order
    reference: tuple[Action, ...] = ()  # the reference's calls (research R6)

    @property
    def rows(self) -> int:
        return 2 * self.aisles - 1

    @property
    def dock(self) -> Cell:
        """In the west corridor, on the shelf row north of the middle aisle."""
        return (0, 2 * (self.aisles // 2) - 1)

    @property
    def drop(self) -> Cell:
        return (self.columns - 1, self.dock[1])

    @property
    def aisle_names(self) -> tuple[str, ...]:
        return tuple(f"aisle {n}" for n in range(1, self.aisles + 1))

    @property
    def reference_steps(self) -> int:
        return len(self.reference)

    @property
    def budget(self) -> int:
        return 3 * self.reference_steps

    @property
    def reference_is_optimal(self) -> bool:
        return False

    def inside(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.columns and 0 <= cell[1] < self.rows

    def shelf(self, cell: Cell) -> bool:
        x, y = cell
        return self.inside(cell) and y % 2 == 1 and 0 < x < self.columns - 1

    def open(self, cell: Cell) -> bool:
        return self.inside(cell) and not self.shelf(cell)

    def corridors(self, cell: Cell) -> tuple[str, ...]:
        """The corridors a cell lies in: its aisle first, then the west or east corridor."""
        x, y = cell
        found = [f"aisle {y // 2 + 1}"] if y % 2 == 0 else []
        if x == 0:
            found.append(WEST)
        if x == self.columns - 1:
            found.append(EAST)
        return tuple(found)

    def corridor_cells(self, name: str) -> tuple[Cell, ...]:
        if name == WEST:
            return tuple((0, y) for y in range(self.rows))
        if name == EAST:
            return tuple((self.columns - 1, y) for y in range(self.rows))
        row = 2 * (int(name.removeprefix("aisle ")) - 1)
        return tuple((x, row) for x in range(self.columns))

    def neighbor(self, cell: Cell, direction: str) -> Cell | None:
        """The open cell one step away, or None at a shelf or the edge."""
        dx, dy = STEP[direction]
        other = (cell[0] + dx, cell[1] + dy)
        return other if self.open(other) else None

    def plan(self) -> tuple[str, ...]:
        """The floor plan as the start view shows it: no packages."""
        rows = []
        for y in range(self.rows):
            marks = ["#" if self.shelf((x, y)) else "." for x in range(self.columns)]
            if y == self.dock[1]:
                marks[0], marks[-1] = "S", "D"
            rows.append("".join(marks))
        return tuple(rows)
