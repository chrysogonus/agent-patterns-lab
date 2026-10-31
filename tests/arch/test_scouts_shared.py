"""The shared scout machinery of A7–A9 (specs/004 contracts/orchestrators.md, research R8, R9)."""

import json

import pytest

from apl.arch.scouts import SharedMap, read_answer
from apl.dungeon import generate, start_episode
from apl.dungeon.env import Episode
from apl.dungeon.frames import build_frames
from apl.dungeon.tools import AgentTools
from tests.arch.oracle import expected_shared


def _board(episode: Episode, scouts: int) -> SharedMap:
    board = SharedMap.from_start(json.dumps(AgentTools(episode).start.to_dict()), 0)
    for _ in range(scouts - 1):
        number = episode.add_scout()
        assert number is not None
        board.add(number)
    return board


_ARGS = {"look": [], "move": ["direction"], "take": ["item"], "use": ["item", "direction"]}


@pytest.mark.parametrize(("level", "seed", "scouts"), [("L2", 1001, 2), ("L3", 1002, 3)])
def test_the_merged_map_matches_what_all_scouts_saw(level: str, seed: int, scouts: int) -> None:
    dungeon = generate(level, seed)
    episode = start_episode(dungeon)
    board = _board(episode, scouts)
    actions = dungeon.solution.actions
    for i in range(30):  # the scouts take turns, each walking the solution from its own start
        scout, action = i % scouts, actions[(i // scouts) % len(actions)]
        args = dict(zip(_ARGS[action.tool], action.args, strict=True))
        result = getattr(episode, action.tool)(*action.args, scout=scout)
        board.apply(scout, action.tool, args, result.to_dict())
        if episode.end_reason is not None:
            break
    log = episode.log
    frames = build_frames(dungeon, [e.action for e in log], scouts=[e.scout for e in log])
    rooms, leads, where, held = expected_shared(dungeon, frames, len(frames) - 1, range(scouts))
    assert set(board.map.rooms) == rooms
    assert {r: n.leads_to for r, n in board.map.rooms.items() if n.leads_to} == leads
    assert board.positions == where and board.inventories == held


def test_render_for_a_scout_and_for_the_orchestrator() -> None:
    episode = start_episode(generate("L2", 1001))
    board = _board(episode, 2)
    direction = next(str(e.direction) for e in episode.describe(scout=1).exits if e.lock is None)
    board.apply(1, "move", {"direction": direction}, episode.move(direction, scout=1).to_dict())
    mine = board.render(0)
    assert "You are in: " in mine and "Other scouts: scout 1 is in " in mine
    orchestrator = board.render(None)
    assert "You are in" not in orchestrator and "(you are here)" not in orchestrator
    assert "Scouts: scout 0 is in " in orchestrator and "; scout 1 is in " in orchestrator
    board.claims[1] = ("k7", "north")
    assert "Claims: scout 1 → k7 north." in board.render(0)


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ('Here is my plan: {"done": true} as asked.', None),
        ("no json here", "no JSON object"),
        ('{"tasks": [', "no JSON object"),
        ('{"tasks": [}', "does not parse"),
        ("[1, 2] {", "no JSON object"),
    ],
)
def test_read_answer(text: str, problem: str | None) -> None:
    found = read_answer(text)
    if problem is None:
        assert found == {"done": True}
    else:
        assert isinstance(found, str) and problem in found
