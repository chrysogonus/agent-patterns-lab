"""One rune-floor episode (specs/010 data-model.md "Episode", research R3, R8–R10)."""

from typing import Any

from apl.rune.env import start_episode
from apl.rune.model import Floor, Rule
from apl.rune.rules import next_state, outcome_of

# A 4×3 floor: S at A2, G at D2. Under red, blue, green the straight row traps at B2.
LAYOUT = [
    ["red", "blue", "green", "red"],
    ["start", "yellow", "red", "goal"],
    ["blue", "green", "blue", "yellow"],
]
SAFE = ["north", "east", "east", "south", "east"]  # A1, B1, C1, C2, D2


CYCLE = Rule("cycle", ("red", "blue", "green"))


def _floor(rule: Rule = CYCLE, reference: int = 5) -> Floor:
    colors = {
        (x, y): w
        for y, row in enumerate(LAYOUT)
        for x, w in enumerate(row)
        if w not in ("start", "goal")
    }
    return Floor(None, None, 4, 3, colors, (0, 1), (3, 1), rule, reference)


def test_the_floor_view_is_free_and_equals_look() -> None:
    episode = start_episode(_floor())
    view = _j(episode.describe())
    assert view == {
        "columns": 4, "rows": 3, "start": "A2", "goal": "D2", "position": "A2",
        "floor": [LAYOUT[0], LAYOUT[1], LAYOUT[2]],
    }  # fmt: skip
    assert episode.steps == 0
    result = episode.look()
    assert result.ok and _j(result)["data"] == view and episode.steps == 1


def test_safe_steps_extend_the_walk_and_the_goal_ends_it() -> None:
    episode = start_episode(_floor())
    result = episode.move("north")
    assert _j(result)["data"] == {"position": "A1", "color": "red"}
    assert episode.position == (0, 0) and episode.walk == [(0, 0)]
    for direction in SAFE[1:-1]:
        episode.move(direction)
    assert episode.walk == [(0, 0), (1, 0), (2, 0), (2, 1)]
    last = episode.move("east")
    assert _j(last)["data"] == {"position": "D2", "goal": True}
    outcome = episode.outcome()
    assert outcome.success and str(outcome.end_reason) == "goal" and outcome.steps == 5
    assert outcome.traps == 0 and outcome.walks == 1


def test_bad_directions_and_edges_cost_a_step_and_change_nothing() -> None:
    episode = start_episode(_floor())
    for raw in ("up", "East", 3, None):
        result = episode.move(raw)
        assert not result.ok and result.error is not None
        assert str(result.error.code) == "invalid_direction"
    assert _j(episode.move("up"))["error"]["message"] == (
        "'up' is not a direction; use north, east, south or west."
    )
    edge = episode.move("west")
    assert _j(edge)["error"] == {"code": "edge", "message": "There is no tile west of A2."}
    assert episode.position == (0, 1) and episode.steps == 6 and episode.invalid_actions == 6


def test_a_trap_sends_the_agent_back_and_starts_a_new_walk() -> None:
    episode = start_episode(_floor())
    result = episode.move("east")  # B2 yellow
    assert result.ok and _j(result)["data"] == {
        "trap": "B2",
        "color": "yellow",
        "position": "A2",
    }
    assert episode.position == (0, 1) and episode.walk == [] and episode.walks == 2
    assert len(episode.traps) == 1 and episode.repeated_traps == 0
    assert episode.invalid_actions == 0


def test_back_on_start_is_a_new_walk_without_a_trap() -> None:
    episode = start_episode(_floor())
    episode.move("north")
    result = episode.move("south")
    assert _j(result)["data"] == {"position": "A2", "color": "start"}
    assert episode.walk == [] and episode.walks == 2 and not episode.traps


def test_repeated_traps_follow_the_rule_state() -> None:
    episode = start_episode(_floor())
    episode.move("east")  # B2 at state 0: trap
    episode.move("east")  # the same again: repeated
    assert len(episode.traps) == 2 and episode.repeated_traps == 1
    # B1 blue is safe at state 1 and a trap at state 0 (from A1 → B1 it is state 1).
    episode.move("north")  # A1 red, state 0 → 1
    episode.move("south")  # back on start
    episode.move("south")  # A3 blue at state 0: trap (a new one)
    assert episode.repeated_traps == 1 and len(episode.traps) == 3


def test_on_r0_the_same_cell_is_always_a_repeat() -> None:
    floor = _floor(Rule("none", (), frozenset({(1, 1)})), reference=3)
    episode = start_episode(floor)
    episode.move("east")
    episode.move("north")
    episode.move("south")  # back on start
    episode.move("east")  # B2 again, from another walk length but the rule has no state
    assert len(episode.traps) == 2 and episode.repeated_traps == 1


def test_a_retrying_architecture_restarts_on_a_trap() -> None:
    episode = start_episode(_floor())
    episode.max_attempts = 3
    restarts: list[int] = []
    episode.on_restart = lambda: restarts.append(episode.attempt)
    result = episode.move("east")
    assert _j(result)["data"] == {
        "trap": "B2", "color": "yellow", "position": "A2", "attempts_left": 2,
    }  # fmt: skip
    assert restarts == [2] and episode.attempt == 2 and episode.steps == 1
    episode.move("east")
    episode.move("east")  # the last attempt: an ordinary trap
    assert episode.attempt == 3 and restarts == [2, 3]
    last = episode.move("east")
    assert "attempts_left" not in _j(last)["data"] and episode.end_reason is None
    assert episode.repeated_traps == 3


def test_restart_puts_the_agent_back_on_start() -> None:
    episode = start_episode(_floor())
    episode.max_attempts = 2
    episode.move("north")
    assert episode.restart()
    assert episode.position == (0, 1) and episode.walk == [] and episode.walks == 2
    assert episode.attempt == 2 and not episode.restart()


def test_the_budget_ends_the_episode_and_the_goal_counts_first() -> None:
    episode = start_episode(_floor(reference=1))  # budget 4
    for _ in range(4):
        episode.move("west")
    assert str(episode.end_reason) == "budget" and episode.outcome().budget_hit
    episode = start_episode(_floor(reference=2))  # budget 8
    for direction in ["west", "west", "west", *SAFE]:
        episode.move(direction)
    assert episode.outcome().success and episode.steps == 8


def test_calls_after_the_end_and_unknown_tools() -> None:
    episode = start_episode(_floor())
    unknown = episode.unknown("jump")
    assert _j(unknown)["error"] == {
        "code": "unknown_tool",
        "message": "There is no tool named 'jump'. The tools are look and move.",
    }
    assert episode.steps == 1
    episode.stop()
    assert str(episode.end_reason) == "stopped"
    after = episode.move("north")
    assert _j(after)["error"]["code"] == "episode_over" and episode.steps == 1
    assert episode.log[-1].step is None


def test_the_outcome_dict_and_counts_rebuilt_from_the_log() -> None:
    floor = _floor()
    episode = start_episode(floor)
    episode.max_attempts = 2
    for direction in ["east", "east", "north", "east", "west", "west", "south", *SAFE]:
        episode.move(direction)
    data = _j(episode.outcome())
    for key in ("traps", "repeated_traps", "walks", "reference_is_optimal", "attempts"):
        assert key in data
    # Rebuild the trap counts from the saved log alone (SC-006).
    cell, state, traps, repeated = floor.start, 0, 0, 0
    seen: set[tuple[tuple[int, int], int]] = set()
    for entry in data["log"]:
        result = entry["result"]
        if not result["ok"]:
            continue
        found = result["data"]
        if "trap" in found:
            trapped = _cell(found["trap"])
            sprung = (trapped, state if floor.rule.kind == "cycle" else 0)
            repeated += sprung in seen
            seen.add(sprung)
            traps += 1
            cell, state = floor.start, 0
        elif "position" in found and not found.get("goal"):
            cell = _cell(found["position"])
            if cell == floor.start:
                state = 0
            elif entry["action"]["tool"] == "move":
                assert outcome_of(floor, state, cell) == "safe"
                state = next_state(floor.rule, state)
    assert (traps, repeated) == (data["traps"], data["repeated_traps"])


def _cell(name: str) -> tuple[int, int]:
    return ("ABCDEFGHIJ".index(name[0]), int(name[1:]) - 1)


def _j(value: Any) -> Any:
    """A result or outcome as JSON-like data, typed loosely for the checks."""
    return value.to_dict()
