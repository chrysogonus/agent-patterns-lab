"""Dungeon layout types. Runner side only: architectures must not import this module."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, cast

Pos = tuple[int, int]  # (x, y): x is the column, y the row, (0, 0) is the north-west corner
Tool = Literal["look", "move", "take", "use", "unknown"]  # unknown: a call to no such tool

_ARITY: dict[str, int] = {"look": 0, "move": 1, "take": 1, "use": 2, "unknown": 1}


class Direction(StrEnum):
    NORTH = "north"
    EAST = "east"
    SOUTH = "south"
    WEST = "west"

    @property
    def delta(self) -> Pos:
        return _DELTAS[self]

    @property
    def opposite(self) -> Direction:
        return _OPPOSITES[self]


_DELTAS = {
    Direction.NORTH: (0, -1),
    Direction.EAST: (1, 0),
    Direction.SOUTH: (0, 1),
    Direction.WEST: (-1, 0),
}
_OPPOSITES = {
    Direction.NORTH: Direction.SOUTH,
    Direction.EAST: Direction.WEST,
    Direction.SOUTH: Direction.NORTH,
    Direction.WEST: Direction.EAST,
}


def neighbor(pos: Pos, direction: Direction) -> Pos:
    dx, dy = direction.delta
    return (pos[0] + dx, pos[1] + dy)


def key_name(color: str) -> str:
    return f"{color} key"


@dataclass(frozen=True, slots=True)
class Level:
    name: str
    size: int
    locks: int
    extra_doors: int
    min_dead_ends: int


LEVELS: dict[str, Level] = {
    "L1": Level("L1", size=3, locks=0, extra_doors=1, min_dead_ends=0),
    "L2": Level("L2", size=4, locks=1, extra_doors=2, min_dead_ends=0),
    "L3": Level("L3", size=5, locks=2, extra_doors=3, min_dead_ends=2),
}


@dataclass(frozen=True, slots=True, order=True)
class Edge:
    """A door position between two neighboring rooms; Edge(a, b) == Edge(b, a)."""

    a: Pos
    b: Pos

    def __post_init__(self) -> None:
        if abs(self.a[0] - self.b[0]) + abs(self.a[1] - self.b[1]) != 1:
            raise ValueError(f"rooms {self.a} and {self.b} are not neighbors")
        if self.b < self.a:
            a, b = self.b, self.a
            object.__setattr__(self, "a", a)
            object.__setattr__(self, "b", b)

    def other(self, pos: Pos) -> Pos:
        return self.b if pos == self.a else self.a

    def to_list(self) -> list[list[int]]:
        return [list(self.a), list(self.b)]


@dataclass(frozen=True, slots=True)
class Layout:
    """Everything about a dungeon except its level, seed and solution."""

    size: int
    doors: frozenset[Edge]
    locks: Mapping[Edge, str]
    keys: Mapping[str, Pos]
    start: Pos
    exit: Pos
    labels: Mapping[Pos, str]

    def rooms(self) -> Iterator[Pos]:
        """All rooms in grid order: row by row, west to east."""
        for y in range(self.size):
            for x in range(self.size):
                yield (x, y)

    def in_grid(self, pos: Pos) -> bool:
        return 0 <= pos[0] < self.size and 0 <= pos[1] < self.size

    def door(self, pos: Pos, direction: Direction) -> Edge | None:
        other = neighbor(pos, direction)
        if not self.in_grid(other):
            return None
        edge = Edge(pos, other)
        return edge if edge in self.doors else None

    def validate(self) -> None:
        """Check the structural rules in data-model.md; raise ValueError on the first broken."""
        if self.size < 2:
            raise ValueError("size must be at least 2")
        if any(not (self.in_grid(e.a) and self.in_grid(e.b)) for e in self.doors):
            raise ValueError("every door must lie inside the grid")
        if not set(self.locks) <= self.doors:
            raise ValueError("every locked door must be a door")
        if len(set(self.locks.values())) != len(self.locks):
            raise ValueError("lock colors must be distinct")
        if set(self.keys) != set(self.locks.values()):
            raise ValueError("there must be exactly one key per lock color")
        if any(not self.in_grid(p) for p in self.keys.values()):
            raise ValueError("every key must lie in a room")
        if not (self.in_grid(self.start) and self.in_grid(self.exit)):
            raise ValueError("start and exit must lie inside the grid")
        if self.start == self.exit:
            raise ValueError("start and exit must differ")
        if set(self.labels) != set(self.rooms()):
            raise ValueError("every room needs exactly one label")
        if len(set(self.labels.values())) != len(self.labels):
            raise ValueError("labels must be unique")

    def to_dict(self) -> dict[str, object]:
        return {
            "size": self.size,
            "doors": [e.to_list() for e in sorted(self.doors)],
            "locks": [{"door": e.to_list(), "color": c} for e, c in sorted(self.locks.items())],
            "keys": {c: list(p) for c, p in sorted(self.keys.items())},
            "start": list(self.start),
            "exit": list(self.exit),
            "labels": [[list(p), label] for p, label in sorted(self.labels.items())],
        }


@dataclass(frozen=True, slots=True)
class Action:
    tool: Tool
    args: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.tool not in _ARITY:
            raise ValueError(f"unknown tool {self.tool!r}")
        if len(self.args) != _ARITY[self.tool]:
            raise ValueError(f"{self.tool} takes {_ARITY[self.tool]} argument(s)")

    @classmethod
    def parse(cls, data: object) -> Action:
        """Build an action from its JSON form, e.g. {"tool": "move", "args": ["east"]}."""
        if not isinstance(data, dict):
            raise ValueError(f"an action must be an object, got {data!r}")
        tool, args = data.get("tool"), data.get("args", [])
        if not isinstance(tool, str) or not isinstance(args, list):
            raise ValueError(f"invalid action {data!r}")
        if not all(isinstance(a, str) for a in args):
            raise ValueError(f"action arguments must be strings: {data!r}")
        return cls(cast(Tool, tool), tuple(args))

    def __str__(self) -> str:
        return " ".join((self.tool, *self.args))

    def to_dict(self) -> dict[str, object]:
        return {"tool": self.tool, "args": list(self.args)}


@dataclass(frozen=True, slots=True)
class Solution:
    actions: tuple[Action, ...]

    @property
    def length(self) -> int:
        return len(self.actions)

    def to_dict(self) -> dict[str, object]:
        return {"actions": [a.to_dict() for a in self.actions], "length": self.length}


@dataclass(frozen=True, slots=True)
class Dungeon:
    level: Level | None  # None for a hand-built dungeon
    seed: int | None
    layout: Layout
    solution: Solution

    @property
    def budget(self) -> int:
        return 3 * self.solution.length

    @classmethod
    def from_layout(cls, layout: Layout) -> Dungeon:
        """A hand-built dungeon: no level or seed, solved here."""
        from apl.dungeon.solver import solve  # the solver imports this module

        layout.validate()
        solution = solve(layout)
        if solution is None:
            raise ValueError("unsolvable layout")
        return cls(None, None, layout, solution)

    def to_dict(self) -> dict[str, object]:
        return {
            "level": self.level.name if self.level else None,
            "seed": self.seed,
            "layout": self.layout.to_dict(),
            "solution": self.solution.to_dict(),
        }
