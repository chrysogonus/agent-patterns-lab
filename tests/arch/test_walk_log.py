"""The walk log: the memory of A2, A3 and A4 on the rune floor (specs/010 contracts)."""

import json

from apl.arch.walk_log import WalkLog
from apl.rune import DEV_SEEDS, AgentTools, generate, start_episode
from apl.rune.model import Floor, Rule
from tests.rune.agents import learner

# A 4×3 floor: S at A2, G at D2; under red, blue, green the straight row traps at B2.
LAYOUT = [
    ["red", "blue", "green", "red"],
    ["start", "yellow", "red", "goal"],
    ["blue", "green", "blue", "yellow"],
]


def _floor() -> Floor:
    colors = {
        (x, y): w
        for y, row in enumerate(LAYOUT)
        for x, w in enumerate(row)
        if w not in ("start", "goal")
    }
    return Floor(
        None, None, 4, 3, colors, (0, 1), (3, 1), Rule("cycle", ("red", "blue", "green")), 5
    )


def _played(moves: list[str]) -> tuple[WalkLog, list[dict[str, object]]]:
    episode = start_episode(_floor())
    tools = AgentTools(episode)
    log = WalkLog.from_start(json.dumps(tools.start.to_dict()))
    results = []
    for direction in moves:
        result = tools.move(direction).to_dict()
        log.apply("move", {"direction": direction}, result)
        results.append(result)
    return log, results


def test_the_render_at_the_start() -> None:
    log, _ = _played([])
    assert log.render() == (
        "Floor: 4 columns × 3 rows. Start A2, goal D2.\n"
        "Row 1: red blue green red\n"
        "Row 2: start yellow red goal\n"
        "Row 3: blue green blue yellow\n"
        "You are on A2.\n"
        "Walks so far:\n"
        "1. (current) none yet"
    )


def test_walks_end_at_traps_at_the_start_and_stay_open() -> None:
    log, _ = _played(["east", "north", "east", "west", "west", "south", "west", "north", "east"])
    # east: trap B2; north A1, east B1, west A1 (state 2 wants green): trap; west: edge (ignored);
    # south A3 blue at state 0: trap; west: edge; north A1 red, east B1 blue.
    assert log.render().split("Walks so far:\n")[1] == (
        "1. none → trap at B2 (yellow)\n"
        "2. A1 red, B1 blue → trap at A1 (red)\n"
        "3. none → trap at A3 (blue)\n"
        "4. (current) A1 red, B1 blue"
    )
    assert "You are on B1." in log.render()
    assert log.known == 4  # B2, A1, B1, A3
    assert log.record((0, 0)) == [(1, "safe"), (3, "trap"), (1, "safe")]
    assert log.record((1, 1)) == [(1, "trap")]


def test_back_on_start_and_failed_calls() -> None:
    log, _ = _played(["north", "south", "up"])
    assert log.render().endswith("1. A1 red → back on start\n2. (current) none yet")
    log.apply("move", {"direction": "up"}, {"ok": False, "error": {}, "data": None})
    assert log.known == 1


def test_look_refreshes_the_floor_and_position() -> None:
    log, _ = _played(["north"])
    log.apply("look", {}, {"ok": True, "error": None, "data": {
        "columns": 4, "rows": 3, "start": "A2", "goal": "D2", "position": "A1",
        "floor": LAYOUT,
    }})  # fmt: skip
    assert "You are on A1." in log.render()


def test_the_log_agrees_with_episodes_on_every_r1_dev_seed() -> None:
    for seed in DEV_SEEDS:
        floor = generate("R1", seed)
        episode = start_episode(floor)
        tools = AgentTools(episode)
        log = WalkLog.from_start(json.dumps(tools.start.to_dict()))
        learner(episode)
        for entry in episode.log:
            data = entry.to_dict()
            args = {"direction": entry.action.args[0]} if entry.action.args else {}
            log.apply(entry.action.tool, args, data["result"])  # type: ignore[arg-type]
        traps = [w for w in log.walks if w.ending.startswith("trap")]
        assert len(traps) == len(episode.traps) == 1
        stepped = {c for w in episode.finished for c in w.cells} | {t.cell for t in episode.traps}
        assert log.known == len(stepped | set(episode.walk))
