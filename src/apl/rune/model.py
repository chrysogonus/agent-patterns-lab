"""The rune floor's data types (specs/010 data-model.md). Runner side only."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

Cell = tuple[int, int]  # (column, row); (0, 0) is A1, the north-west corner

COLORS = ("red", "blue", "green", "yellow")
COLUMNS = "ABCDEFGHIJ"
DIRECTIONS = ("north", "east", "south", "west")
STEP: dict[str, Cell] = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}


def cell_name(cell: Cell) -> str:
    return COLUMNS[cell[0]] + str(cell[1] + 1)


@dataclass(frozen=True, slots=True)
class RuneLevel:
    name: str
    columns: int
    rows: int
    rule: str  # none, cycle3, cycle4, rows (research R4)


LEVELS: dict[str, RuneLevel] = {
    "R0": RuneLevel("R0", 7, 5, "none"),
    "R1": RuneLevel("R1", 7, 5, "cycle3"),
    "R2": RuneLevel("R2", 9, 7, "cycle4"),
    "R3": RuneLevel("R3", 9, 7, "rows"),
}


@dataclass(frozen=True, slots=True)
class Rule:
    """What decides whether a step is safe. Hidden: it never reaches an architecture."""

    kind: str  # none, cycle, rows
    colors: tuple[str, ...] = ()  # the cycle; or (odd-row color, even-row color)
    traps: frozenset[Cell] = field(default_factory=frozenset)  # R0's trap cells


@dataclass(frozen=True, slots=True)
class Floor:
    level: RuneLevel | None  # None for a hand-built floor
    seed: int | None
    columns: int
    rows: int
    colors: Mapping[Cell, str]  # every cell but the start and the goal
    start: Cell
    goal: Cell
    rule: Rule
    reference: int  # moves on the shortest safe path (research R6)

    @property
    def reference_steps(self) -> int:
        return self.reference

    @property
    def budget(self) -> int:
        return 4 * self.reference  # spec FR-009

    @property
    def reference_is_optimal(self) -> bool:
        return True  # an exact search (research R6)

    def neighbor(self, cell: Cell, direction: str) -> Cell | None:
        """The cell one step away, or None off the floor."""
        dx, dy = STEP[direction]
        x, y = cell[0] + dx, cell[1] + dy
        if 0 <= x < self.columns and 0 <= y < self.rows:
            return (x, y)
        return None

    def word(self, cell: Cell) -> str:
        """The cell as the agent reads it: a color, or start or goal."""
        if cell == self.start:
            return "start"
        if cell == self.goal:
            return "goal"
        return self.colors[cell]


@dataclass(frozen=True, slots=True)
class Action:
    tool: str  # look, move, or unknown
    args: tuple[str, ...] = ()

    def __str__(self) -> str:
        return " ".join((self.tool, *self.args))

    def to_dict(self) -> dict[str, object]:
        return {"tool": self.tool, "args": list(self.args)}
