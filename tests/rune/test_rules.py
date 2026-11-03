"""The rune floor's rules and the reference search (specs/010 research R3, R4, R6)."""

import itertools
import random

from apl.rune.model import COLORS, DIRECTIONS, Cell, Floor, Rule
from apl.rune.rules import allows, describe, next_state, outcome_of, reference_path

CYCLE = Rule("cycle", ("red", "blue", "green"))
ROWS = Rule("rows", ("blue", "yellow"))

# A 4×3 floor: S at A2, G at D2. The straight row (B2 yellow) traps under CYCLE.
LAYOUT = [
    ["red", "blue", "green", "red"],
    ["start", "yellow", "red", "goal"],
    ["blue", "green", "blue", "yellow"],
]


def _floor(rule: Rule, layout: list[list[str]] = LAYOUT) -> Floor:
    colors = {
        (x, y): word
        for y, row in enumerate(layout)
        for x, word in enumerate(row)
        if word not in ("start", "goal")
    }
    rows, columns = len(layout), len(layout[0])
    return Floor(
        None, None, columns, rows, colors, (0, rows // 2), (columns - 1, rows // 2), rule, 0
    )


def test_allows_for_each_rule_kind() -> None:
    floor = _floor(CYCLE)
    assert allows(CYCLE, floor.colors, (0, 0), 0)  # red first
    assert not allows(CYCLE, floor.colors, (1, 1), 0)  # yellow is never in the cycle
    assert allows(CYCLE, floor.colors, (1, 0), 1) and not allows(CYCLE, floor.colors, (1, 0), 0)
    traps = Rule("none", (), frozenset({(1, 1)}))
    assert not allows(traps, floor.colors, (1, 1), 5) and allows(traps, floor.colors, (2, 1), 0)
    # rows: row 1 (y = 0) and row 3 allow blue, row 2 allows yellow.
    assert allows(ROWS, floor.colors, (1, 0), 0) and not allows(ROWS, floor.colors, (0, 0), 0)
    assert allows(ROWS, floor.colors, (1, 1), 7) and not allows(ROWS, floor.colors, (2, 1), 0)
    assert allows(ROWS, floor.colors, (0, 2), 0)


def test_next_state() -> None:
    assert [next_state(CYCLE, s) for s in range(3)] == [1, 2, 0]
    assert next_state(Rule("cycle", ("red", "red", "blue", "green")), 3) == 0
    assert next_state(ROWS, 4) == 0 and next_state(Rule("none"), 2) == 0


def test_outcome_of_start_goal_trap_and_safe() -> None:
    floor = _floor(CYCLE)
    assert outcome_of(floor, 2, floor.start) == "start"
    assert outcome_of(floor, 2, floor.goal) == "goal"
    assert outcome_of(floor, 0, (1, 1)) == "trap"
    assert outcome_of(floor, 0, (0, 0)) == "safe"


def test_reference_path_on_the_hand_built_floor() -> None:
    floor = _floor(CYCLE)
    # S → A1 red → B1 blue → C1 green → D1 red → D2 goal (east before south on the tie with C2).
    assert reference_path(floor) == [(0, 1), (0, 0), (1, 0), (2, 0), (3, 0), (3, 1)]


def test_stepping_back_onto_a_cell_counts_toward_the_state() -> None:
    floor = _floor(Rule("cycle", ("red", "red", "blue")))
    # A1 red (state 0 → 1); back to A1? not a neighbour of itself; A1 → B1 blue at state 1 traps.
    assert outcome_of(floor, 1, (1, 0)) == "trap"
    # A1 red at state 1 is allowed (the second red of the cycle).
    assert outcome_of(floor, 1, (0, 0)) == "safe"


def _brute(floor: Floor, depth: int) -> int | None:
    """The fewest moves to G, by trying every move sequence up to `depth` (off-floor moves cut)."""
    for n in range(1, depth + 1):
        for seq in itertools.product(DIRECTIONS, repeat=n):
            cell, state, ok = floor.start, 0, True
            for i, direction in enumerate(seq):
                other = floor.neighbor(cell, direction)
                if other is None:
                    ok = False
                    break
                what = outcome_of(floor, state, other)
                if what == "goal":
                    if i == n - 1:
                        return n
                    ok = False
                    break
                if what in ("start", "trap"):
                    cell, state = floor.start, 0
                else:
                    cell, state = other, next_state(floor.rule, state)
            if not ok:
                continue
    return None


def _random_floor(rng: random.Random, rule: Rule) -> Floor:
    layout = [[rng.choice(COLORS) for _ in range(4)] for _ in range(3)]
    layout[1][0], layout[1][3] = "start", "goal"
    return _floor(rule, layout)


def test_the_search_agrees_with_brute_force() -> None:
    rng = random.Random("rune-brute")
    rules = [
        CYCLE,
        Rule("cycle", ("red", "red", "blue", "green")),
        ROWS,
        Rule("none", (), frozenset({(1, 1), (2, 0)})),
    ]
    for rule in rules:
        for _ in range(6):
            floor = _random_floor(rng, rule)
            path = reference_path(floor)
            expected = _brute(floor, 7)
            got = None if path is None else len(path) - 1
            if got is not None and got > 7:
                continue  # beyond the brute force's depth
            assert got == expected, (rule, floor.colors)


def test_reference_path_steps_are_allowed_and_ties_go_north_first() -> None:
    floor = _floor(Rule("none"), [["red"] * 3, ["start", "red", "goal"], ["red"] * 3])
    assert reference_path(floor) == [(0, 1), (1, 1), (2, 1)]
    blocked = _floor(
        Rule("none", (), frozenset({(1, 1)})), [["red"] * 3, ["start", "red", "goal"], ["red"] * 3]
    )
    assert reference_path(blocked) == [(0, 1), (0, 0), (1, 0), (2, 0), (2, 1)]
    walled = Rule("none", (), frozenset({(1, 0), (1, 1), (1, 2)}))
    assert (
        reference_path(_floor(walled, [["red"] * 3, ["start", "red", "goal"], ["red"] * 3])) is None
    )


def test_describe() -> None:
    assert describe(CYCLE) == "colors cycle: red, blue, green"
    assert describe(ROWS) == "odd rows blue, even rows yellow"
    assert describe(Rule("none", (), frozenset({(1, 1)}))) == "fixed trap cells"


def test_states_of_a_walk() -> None:
    cells: list[Cell] = [(0, 0), (1, 0), (2, 0)]
    floor = _floor(CYCLE)
    state = 0
    for cell in cells:
        assert outcome_of(floor, state, cell) == "safe"
        state = next_state(CYCLE, state)
    assert state == 0
