"""The survey field's data types (specs/005 data-model.md). Runner side only."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

Cell = tuple[int, int]  # (column, row); (0, 0) is A1, the north-west corner
Wall = frozenset[Cell]  # two neighboring cells

COLUMNS = "ABCDEFGHIJ"
DIRECTIONS = ("north", "east", "south", "west")
STEP: dict[str, Cell] = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}


def cell_name(cell: Cell) -> str:
    return COLUMNS[cell[0]] + str(cell[1] + 1)


def wall(a: Cell, b: Cell) -> Wall:
    return frozenset((a, b))


@dataclass(frozen=True, slots=True)
class SurveyLevel:
    name: str
    size: int
    deposits: int
    walls: int  # interior wall segments
    min_dead_ends: int  # cells with exactly one exit


LEVELS: dict[str, SurveyLevel] = {
    "S1": SurveyLevel("S1", size=6, deposits=6, walls=0, min_dead_ends=0),
    "S2": SurveyLevel("S2", size=10, deposits=15, walls=0, min_dead_ends=0),
    "S3": SurveyLevel("S3", size=10, deposits=15, walls=18, min_dead_ends=3),
}


@dataclass(frozen=True, slots=True)
class Action:
    tool: str  # look, move, submit, or unknown
    args: tuple[str, ...] = ()

    def __str__(self) -> str:
        return " ".join((self.tool, *self.args))

    def to_dict(self) -> dict[str, object]:
        return {"tool": self.tool, "args": list(self.args)}


@dataclass(frozen=True, slots=True)
class Field:
    level: SurveyLevel | None  # None for a hand-built field
    seed: int | None
    size: int
    walls: frozenset[Wall]
    deposits: frozenset[Cell]
    walk: tuple[str, ...]  # the reference walk from `start` (research R8)
    reference_is_optimal: bool
    start: Cell = (0, 0)

    @property
    def cells(self) -> int:
        return self.size * self.size

    @property
    def true_total(self) -> int:
        return len(self.deposits)

    @property
    def reference_steps(self) -> int:
        return len(self.walk) + 1  # the walk, then the submission

    @property
    def budget(self) -> int:
        return 3 * self.reference_steps

    def all_cells(self) -> Iterator[Cell]:
        """Row by row, west to east."""
        for row in range(self.size):
            for col in range(self.size):
                yield (col, row)

    def neighbor(self, cell: Cell, direction: str) -> Cell | None:
        """The cell one step away, or None past the edge or through a wall."""
        dx, dy = STEP[direction]
        other = (cell[0] + dx, cell[1] + dy)
        if not (0 <= other[0] < self.size and 0 <= other[1] < self.size):
            return None
        return None if wall(cell, other) in self.walls else other

    def exits(self, cell: Cell) -> tuple[str, ...]:
        return tuple(d for d in DIRECTIONS if self.neighbor(cell, d) is not None)
