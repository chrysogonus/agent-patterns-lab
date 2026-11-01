"""The shared scout machinery of A7–A9 (specs/004 contracts/orchestrators.md, research R8, R9)."""

import copy
import json
from collections import Counter
from typing import Any

import pytest
from langchain_core.messages import AIMessage

from apl.arch.rounds import ROUNDS_INSTRUCTIONS
from apl.arch.scouts import ScoutGraph, ScoutState, SharedMap, act, read_answer
from apl.dungeon import generate, start_episode
from apl.dungeon.env import Episode
from apl.dungeon.frames import build_frames
from apl.dungeon.model import Dungeon, key_name
from apl.dungeon.tools import AgentTools
from apl.kit import build_kit
from tests.arch.oracle import expected_board, expected_shared
from tests.arch.orchestrated import play
from tests.dungeon.reference import locked_shortcut_wins, two_open_routes
from tests.runner.scripted import (
    ScriptedChatModel,
    Strategy,
    by_system,
    json_answer,
    tool_calls,
    walk_solution,
)


def _board(episode: Episode, scouts: int) -> SharedMap[Any]:
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


def _all_walk(level: str, seed: int) -> Strategy:
    return walk_solution(generate(level, seed))


def _rounds_walk(level: str, seed: int) -> Strategy:
    plan = {"tasks": [{"scout": n, "task": "walk", "steps": 3} for n in (0, 1)]}
    return by_system({ROUNDS_INSTRUCTIONS[:60]: json_answer(plan)}, _all_walk(level, seed))


@pytest.mark.parametrize("arch", ["rounds", "blackboard"])
@pytest.mark.parametrize(("level", "seed"), [("L2", 1001), ("L3", 1002), ("L3", 1004)])
def test_the_board_matches_all_tool_results_after_every_call(
    arch: str, level: str, seed: int, monkeypatch: pytest.MonkeyPatch
) -> None:  # SC-003, US2/AC2
    snapshots: list[tuple[int, SharedMap[Any]]] = []
    apply = SharedMap.apply

    def spy(self: SharedMap[Any], scout: int, name: str, args: Any, result: Any) -> None:
        apply(self, scout, name, args, result)
        snapshots.append((id(self), copy.deepcopy(self)))

    monkeypatch.setattr(SharedMap, "apply", spy)
    strategy = _rounds_walk(level, seed) if arch == "rounds" else _all_walk(level, seed)
    result = play(arch, level, seed, strategy)
    assert result.outcome is not None
    log = result.outcome.log
    counts = Counter(i for i, _ in snapshots)
    board_id = next(i for i, n in counts.items() if n == max(counts.values()))
    boards = [b for i, b in snapshots if i == board_id]
    assert len({e.scout for e in log}) >= 2  # several scouts really acted
    assert len(boards) == len(log) - 1  # the move into the exit ends the episode first
    dungeon = generate(level, seed)
    actors = [e.scout for e in log]
    frames = build_frames(dungeon, [e.action for e in log], scouts=actors)
    start = dungeon.layout.labels[dungeon.layout.start]
    for k, board in enumerate(boards, 1):  # the k-th applied call is log entry k
        expected = expected_board(dungeon, frames, actors, k)
        assert board.map.rooms == expected.rooms, k
        assert board.map.opened == expected.opened, k
        for n in board.positions:
            view = frames[k].scouts[n] if n < len(frames[k].scouts) else None
            room = dungeon.layout.labels[view.position] if view else start
            held = tuple(key_name(c) for c in view.inventory) if view else ()
            assert (board.positions[n], board.inventories[n]) == (room, held), (k, n)


def test_a_newer_observation_replaces_an_older_one() -> None:  # spec edge case
    episode = start_episode(Dungeon.from_layout(locked_shortcut_wins()))
    board = _board(episode, 2)
    board.apply(0, "move", {"direction": "east"}, episode.move("east").to_dict())
    assert board.map.rooms["a3"].exits["east"] == "red"  # scout 0 saw it locked
    for name, args in (("move", {"direction": "east"}), ("take", {"item": "red key"}),
                       ("use", {"item": "red key", "direction": "east"})):  # fmt: skip
        result = getattr(episode, name)(*args.values(), scout=1)
        board.apply(1, name, args, result.to_dict())
    assert board.map.rooms["a3"].exits["east"] is None and board.map.rooms["a3"].items == []
    assert board.inventories == {0: (), 1: ("red key",)}


def test_act_applies_replies_in_scout_order() -> None:
    episode = start_episode(Dungeon.from_layout(two_open_routes()))
    kit = build_kit(episode, ScriptedChatModel(strategy=lambda m: AIMessage("")))
    board = SharedMap.from_start(kit.start, 0)
    scouts = [ScoutState(0, kit.tool_node, kit.start, board)]
    added = kit.add_scout()
    assert added is not None
    board.add(1)
    scouts.append(ScoutState(1, added.tool_node, added.start, board))
    replies = [(1, tool_calls(("move", {"direction": "south"}))),
               (0, tool_calls(("move", {"direction": "east"})))]  # fmt: skip
    state: ScoutGraph = {"scouts": scouts, "replies": replies, "board": board, "steps": 0}
    out = act(state)
    assert [e.scout for e in episode.log] == [0, 1] and out["steps"] == 2
    assert board.positions == {0: "a3", 1: "a5"}
