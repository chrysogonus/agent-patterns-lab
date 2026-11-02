"""Rune floors from a level and a seed (specs/010 research R4, R5, R7). Runner side only."""

import dataclasses
import random
from collections import deque

from apl.rune.model import COLORS, DIRECTIONS, LEVELS, STEP, Cell, Floor, Rule, RuneLevel
from apl.rune.rules import next_state, outcome_of, reference_path

MAX_TRIES = 1000
EXTRA_MOVES = 6  # a planted path is at most this much longer than the straight row
TRAP_SHARE = 0.35  # R0: the share of cells off the planted path that are traps
EAST_WEIGHT = 3  # the planted path leans east


def generate(level: str, seed: int) -> Floor:
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r} (levels: {', '.join(LEVELS)})")
    spec = LEVELS[level]
    rng = random.Random(f"rune:{level}:{seed}")
    start, goal = (0, spec.rows // 2), (spec.columns - 1, spec.rows // 2)
    for _ in range(MAX_TRIES):
        rule = _rule(spec.rule, rng)
        path = _planted_path(spec, start, goal, rng)
        if path is None:
            continue
        colors = {
            (x, y): rng.choice(COLORS)
            for y in range(spec.rows)
            for x in range(spec.columns)
            if (x, y) not in (start, goal)
        }
        for i, cell in enumerate(path[1:-1]):
            if rule.kind == "cycle":
                colors[cell] = rule.colors[i % len(rule.colors)]
            elif rule.kind == "rows":
                colors[cell] = rule.colors[cell[1] % 2]
        if rule.kind == "none":
            on_path = set(path)
            traps = frozenset(
                c for c in sorted(colors) if c not in on_path and rng.random() < TRAP_SHARE
            )
            rule = Rule("none", (), traps)
        floor = Floor(spec, seed, spec.columns, spec.rows, colors, start, goal, rule, 0)
        found = reference_path(floor)
        if found is None or len(found) - 1 <= spec.columns - 1:
            continue  # no safe path, or the straight row is safe
        floor = dataclasses.replace(floor, reference=len(found) - 1)
        if rule.kind == "none" and memory_only_steps(floor) is None:
            continue  # R0 is the control: remembering traps must be enough
        return floor
    raise RuntimeError(f"no {level} floor for seed {seed} in {MAX_TRIES} tries")


def _rule(kind: str, rng: random.Random) -> Rule:
    if kind == "cycle3":
        return Rule("cycle", tuple(rng.sample(COLORS, 3)))
    if kind == "cycle4":
        a, b, c = rng.sample(COLORS, 3)
        return Rule("cycle", (a, a, b, c))
    if kind == "rows":
        return Rule("rows", tuple(rng.sample(COLORS, 2)))
    return Rule("none")


def _planted_path(
    spec: RuneLevel, start: Cell, goal: Cell, rng: random.Random
) -> list[Cell] | None:
    """A random self-avoiding walk from S to G that leans east, at most EXTRA_MOVES longer than
    the straight row."""
    longest = spec.columns - 1 + EXTRA_MOVES
    for _ in range(200):
        path, seen, cell = [start], {start}, start
        while cell != goal and len(path) <= longest:
            options: list[Cell] = []
            for direction in DIRECTIONS:
                dx, dy = STEP[direction]
                other = (cell[0] + dx, cell[1] + dy)
                if 0 <= other[0] < spec.columns and 0 <= other[1] < spec.rows and other not in seen:
                    options += [other] * (EAST_WEIGHT if direction == "east" else 1)
            if not options:
                break
            cell = rng.choice(options)
            path.append(cell)
            seen.add(cell)
        if cell == goal and len(path) - 1 <= longest:
            return path
    return None


def memory_only_steps(floor: Floor) -> int | None:
    """The steps an agent that knows no rule needs to reach G, or None if the budget runs out.

    It remembers (cell, walk length) for every trap and walks the shortest route that avoids
    what it remembers, treating unknown cells as safe (research R7). The tests play the same agent
    through an episode (`tests/rune/agents.py`) and check both agree.
    """
    bad: set[tuple[Cell, int]] = set()
    steps = 0
    while True:
        route = _route(floor, bad)
        if route is None:
            return None
        state = 0
        cell = floor.start
        for i, direction in enumerate(route):
            other = floor.neighbor(cell, direction)
            assert other is not None
            steps += 1
            what = outcome_of(floor, state, other)
            if what == "goal":
                return steps
            if steps >= floor.budget:
                return None
            if what == "trap":
                bad.add((other, i))
                break
            cell, state = other, next_state(floor.rule, state)


def _route(floor: Floor, bad: set[tuple[Cell, int]]) -> list[str] | None:
    first = (floor.start, 0)
    prev: dict[tuple[Cell, int], tuple[tuple[Cell, int], str] | None] = {first: None}
    queue = deque([first])
    while queue:
        cell, i = queue.popleft()
        for direction in DIRECTIONS:
            other = floor.neighbor(cell, direction)
            if other is None or other == floor.start:
                continue
            if other == floor.goal:
                route = [direction]
                node = (cell, i)
                while (link := prev[node]) is not None:
                    node, step = link
                    route.append(step)
                return route[::-1]
            key = (other, i + 1)
            if (other, i) in bad or key in prev or i + 1 > floor.budget:
                continue
            prev[key] = ((cell, i), direction)
            queue.append(key)
    return None
