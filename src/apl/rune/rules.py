"""The rune floor's rules and the reference search (specs/010 research R3, R4, R6). Runner side.

`outcome_of` is the one place the move physics live; the environment, the frames, the generator and
the tests use it.
"""

from collections import deque
from collections.abc import Mapping
from typing import Literal

from apl.rune.model import DIRECTIONS, Cell, Floor, Rule

Outcome = Literal["safe", "trap", "start", "goal"]


def allows(rule: Rule, colors: Mapping[Cell, str], cell: Cell, state: int) -> bool:
    """Whether stepping on a colored cell is safe in this rule state."""
    if rule.kind == "none":
        return cell not in rule.traps
    if rule.kind == "cycle":
        return colors[cell] == rule.colors[state % len(rule.colors)]
    if rule.kind == "rows":
        return colors[cell] == rule.colors[cell[1] % 2]  # row 1 (y = 0) is odd
    raise ValueError(f"unknown rule kind {rule.kind!r}")


def next_state(rule: Rule, state: int) -> int:
    """The state after one more safe cell: the walk's length modulo the cycle, else 0."""
    return (state + 1) % len(rule.colors) if rule.kind == "cycle" else 0


def outcome_of(floor: Floor, state: int, cell: Cell) -> Outcome:
    """What stepping onto `cell` does, with the walk in `state` (research R3)."""
    if cell == floor.start:
        return "start"
    if cell == floor.goal:
        return "goal"
    return "safe" if allows(floor.rule, floor.colors, cell, state) else "trap"


def reference_path(floor: Floor) -> list[Cell] | None:
    """One shortest safe path from S to G, both included, or None.

    Breadth-first over (cell, state) from (S, 0); ties go north, east, south, west.
    """
    first = (floor.start, 0)
    parent: dict[tuple[Cell, int], tuple[Cell, int] | None] = {first: None}
    queue = deque([first])
    while queue:
        node = queue.popleft()
        cell, state = node
        for direction in DIRECTIONS:
            other = floor.neighbor(cell, direction)
            if other is None:
                continue
            what = outcome_of(floor, state, other)
            if what == "goal":
                path = [other]
                link: tuple[Cell, int] | None = node
                while link is not None:
                    path.append(link[0])
                    link = parent[link]
                return path[::-1]
            if what != "safe":
                continue  # back on S or a trap never shortens a path
            key = (other, next_state(floor.rule, state))
            if key not in parent:
                parent[key] = node
                queue.append(key)
    return None


def describe(rule: Rule) -> str:
    """The rule in words, for the experimenter (never for an architecture)."""
    if rule.kind == "cycle":
        return "colors cycle: " + ", ".join(rule.colors)
    if rule.kind == "rows":
        return f"odd rows {rule.colors[0]}, even rows {rule.colors[1]}"
    return "fixed trap cells"
