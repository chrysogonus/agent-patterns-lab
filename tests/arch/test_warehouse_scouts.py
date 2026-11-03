"""A7–A9 with robots on the warehouse (specs/012 FR-023, contracts/architectures.md)."""

import json
import re

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.blackboard import WAREHOUSE_TASK
from apl.arch.fanout import WAREHOUSE_FANOUT_INSTRUCTIONS
from apl.arch.floor_map import FloorMap
from apl.arch.rounds import WAREHOUSE_ROUNDS_INSTRUCTIONS
from apl.arch.scouts import ROBOT_INSTRUCTIONS, SharedMap
from apl.warehouse import generate, start_episode
from apl.warehouse.kit import build_kit
from apl.warehouse.model import Floor, cell_name, parse_cell
from apl.warehouse.plans import blind_split, path
from tests.arch.orchestrated import recording, roles, text
from tests.arch.warehouse_play import play, robot_actions, robots
from tests.runner.scripted import Strategy, by_system, json_answer, tool_calls


def test_the_shared_map_takes_a_floor_map() -> None:
    kit = build_kit(start_episode(generate("P2", 1000)), model=None)  # type: ignore[arg-type]
    board = SharedMap.from_start(kit.start, 0)
    assert isinstance(board.map, FloorMap) and board.positions == {0: "A2"}
    board.add(1)
    picked = {"ok": True, "error": None, "data": {"picked": "package 2", "cell": "F1"}}
    board.apply(1, "pick", {}, picked)
    assert board.inventories == {0: (), 1: ("package 2",)}
    shown = board.render(0)
    assert "Other robots: robot 1 is in A2 carrying package 2." in shown
    assert "Robots: robot 0 is in A2 carrying nothing; robot 1" in board.render(None)


def _fanout(level: str, seed: int) -> tuple[object, list[list[BaseMessage]]]:
    actions = robot_actions(blind_split(generate(level, seed)))
    tasks = [{"task": f"clear your share {n}", "steps": len(a) + 5} for n, a in actions.items()]
    orchestrator = json_answer({"scouts": tasks})
    seen: list[list[BaseMessage]] = []
    strategy = by_system({WAREHOUSE_FANOUT_INSTRUCTIONS: orchestrator}, robots(actions))
    return play("fanout", level, seed, recording(strategy, seen)), seen


def test_fanout_splits_once_and_leaves_a_robot_idle() -> None:
    result, seen = _fanout("P2", 1000)
    row = result.row  # type: ignore[attr-defined]
    assert row.success and row.delivered == 3 and row.scouts == 3
    assert row.idle_robot_turns > 0 and row.orchestrator_calls == 1  # no collect step
    scout = next(m for m in seen if "You are robot 1." in text(m))
    assert ROBOT_INSTRUCTIONS in str(scout[0].content)


def _task_robots(floor: Floor) -> Strategy:
    """Robots that follow only their task line and their map: "go to aisle <n>" walks to the
    aisle's nearest cell; "fetch <cell>" walks there, picks, carries the package to D, drops."""

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        task = re.search(r"Your task: (.+)", text(messages[:2]))
        here = re.search(r"You are in: (\w+) .*You carry: ([^.]+)\.", str(messages[-1].content))
        assert task and here
        cell, carrying = parse_cell(here[1]), here[2] != "nothing"
        if aisle := re.fullmatch(r"go to (aisle \d+)", task[1]):
            cells = floor.corridor_cells(aisle[1])
            goal = min(cells, key=lambda c: (len(path(floor, cell, c)), c[1], c[0]))
            if cell == goal:
                return AIMessage("Arrived.")
            return tool_calls(("move", {"direction": path(floor, cell, goal)[0]}))
        target = parse_cell(task[1].removeprefix("fetch "))
        if carrying:
            if cell == floor.drop:
                return tool_calls(("drop", {}))
            return tool_calls(("move", {"direction": path(floor, cell, floor.drop)[0]}))
        if "delivered_package" in text(messages[2:-1]):
            return AIMessage("Delivered.")
        if cell == target:
            return tool_calls(("pick", {}))
        return tool_calls(("move", {"direction": path(floor, cell, target)[0]}))

    return strategy


def test_rounds_reassigns_the_idle_robot_from_the_merged_map() -> None:
    floor = generate("P2", 1000)
    assigned: dict[int, str] = {}

    def orchestrator(messages: list[BaseMessage]) -> AIMessage:
        prompt = text(messages)
        if "This is the first round." in prompt:
            go = [{"scout": n, "task": f"go to aisle {n + 1}", "steps": 10} for n in range(3)]
            return json_answer({"tasks": go})(messages)
        listed = re.search(r"Packages seen: (.+)\.", prompt)
        if not listed or listed[1] == "none" or assigned:
            return json_answer({"done": True})(messages)
        seen = [parse_cell(c) for c in re.findall(r"package \d+ at (\w+)", listed[1])]
        by_aisle = {n: [c for c in seen if c[1] == 2 * n] for n in range(3)}
        idle = next(n for n, cells in by_aisle.items() if not cells)
        crowded = next(n for n, cells in by_aisle.items() if len(cells) == 2)
        here = floor.corridor_cells(f"aisle {crowded + 1}")[0]
        near, far = sorted(by_aisle[crowded], key=lambda c: len(path(floor, here, c)))
        plan = {crowded: near, idle: far}
        plan |= {n: cells[0] for n, cells in by_aisle.items() if len(cells) == 1}
        assigned.update({n: cell_name(c) for n, c in plan.items()})
        tasks = [{"scout": n, "task": f"fetch {c}", "steps": 40} for n, c in assigned.items()]
        return json_answer({"tasks": tasks})(messages)

    seen: list[list[BaseMessage]] = []
    strategy = by_system({WAREHOUSE_ROUNDS_INSTRUCTIONS: orchestrator}, _task_robots(floor))
    result = play("rounds", "P2", 1000, recording(strategy, seen))
    planning = [m for m in seen if WAREHOUSE_ROUNDS_INSTRUCTIONS in str(m[0].content)]
    unseen = next(x for x in text(planning[1]).splitlines() if "Not seen yet:" in x)
    assert not any(a in unseen.split("Not seen yet:")[1] for a in floor.aisle_names)
    idle = next(n for n in range(3) if not any(c[1] == 2 * n for _, c in floor.packages))
    assert result.outcome is not None
    log = [e for e in result.outcome.log if e.scout == idle and e.result.ok]
    picks = [e.result.data for e in log if e.action.tool == "pick"]
    assert [p.cell for p in picks] == [assigned[idle]]
    assert any(e.action.tool == "drop" for e in log)
    assert result.row.success and result.row.delivered == 3
    fanout, _ = _fanout("P2", 1000)
    assert result.row.parallel_turns < fanout.row.parallel_turns  # type: ignore[attr-defined]


def test_blackboard_robots_claim_packages_and_aisles() -> None:
    seen: list[list[BaseMessage]] = []
    turns = iter(range(100))

    def robot(messages: list[BaseMessage]) -> AIMessage:
        n = next(turns)
        reply = tool_calls(("look", {}))
        claim = "claim: package 2" if n == 0 else "claim: aisle 3" if n == 1 else ""
        return reply.model_copy(update={"content": claim})

    result = play("blackboard", "P2", 1000, recording(robot, seen))
    assert WAREHOUSE_TASK in text(seen[0])
    later = text(seen[2])
    assert "Claims: robot 0 → package 2; robot 1 → aisle 3." in later
    assert "scout" not in later.split("Claims:")[1]
    assert set(roles(result)) <= {"scout 0", "scout 1", "scout 2", "scout 3"}


def test_a_package_claim_is_no_claim_on_the_dungeon() -> None:
    seen: list[list[BaseMessage]] = []

    def scout(messages: list[BaseMessage]) -> AIMessage:
        reply = tool_calls(("look", {}))
        return reply.model_copy(update={"content": "claim: package 2"})

    from tests.arch.orchestrated import play as play_dungeon

    play_dungeon("blackboard", "L1", 1000, recording(scout, seen))
    assert all("Claims:" not in text(m) for m in seen)
    assert json.dumps(None) == "null"
