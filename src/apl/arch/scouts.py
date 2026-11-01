"""Shared by the orchestrators A7–A9: scouts, the merged map and the lockstep turn.

A scout is A2's map-state agent with a task. In each lockstep turn the active scouts' model calls
run in parallel, then `act` applies their tool calls in scout order, so an episode plays the same
way every time (specs/004 research R3, R7–R9). Maps come only from tool results
(Constitution II). Written by the agent at the experimenter's request.
"""

import copy
import json
import operator
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Protocol, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.types import Send

from apl.arch.dungeon_map import DungeonMap
from apl.arch.mapstate import MAP_INSTRUCTIONS
from apl.kit import Kit, ToolNode

# Explains the task line and the other scouts; no advice on how to explore.
SCOUT_INSTRUCTIONS = """\
You are one of several scouts in the same dungeon; each has its own position and inventory. The \
line starting with "Your task:" says what to do. When the task is done or cannot be done, answer \
without a tool call and say briefly what you found."""

_CLAIM = re.compile(r"^claim: (\S+) (north|east|south|west)\s*$", re.MULTILINE)


@dataclass
class SharedMap:
    """One map of what all its scouts saw, plus each scout's room and inventory (research R8)."""

    map: DungeonMap
    start: str  # the start room's label, where new scouts appear
    positions: dict[int, str]
    inventories: dict[int, tuple[str, ...]]
    claims: dict[int, tuple[str, str]] = field(default_factory=dict)  # blackboard only

    @classmethod
    def from_start(cls, start_json: str, scout: int) -> "SharedMap":
        found = DungeonMap.from_start(start_json)
        return cls(found, found.current, {scout: found.current}, {scout: found.inventory})

    def add(self, scout: int) -> None:
        self.positions[scout], self.inventories[scout] = self.start, ()

    def apply(self, scout: int, name: str, args: Any, result: Any) -> None:
        """One tool call of one scout, seen from that scout (DungeonMap.apply's rules)."""
        self.map.current, self.map.inventory = self.positions[scout], self.inventories[scout]
        self.map.apply(name, args, result)
        self.positions[scout], self.inventories[scout] = self.map.current, self.map.inventory

    def render(self, viewer: int | None) -> str:
        """The map as `viewer` sees it, or as the orchestrator sees it (None)."""
        current, inventory = self.map.current, self.map.inventory
        if viewer is not None:
            self.map.current, self.map.inventory = self.positions[viewer], self.inventories[viewer]
        else:
            self.map.current = ""  # no "you are here" for the orchestrator
        lines = self.map.render().split("\n")
        self.map.current, self.map.inventory = current, inventory
        scouts = [
            f"scout {n} is in {room} and holds {', '.join(self.inventories[n]) or 'nothing'}"
            for n, room in sorted(self.positions.items())
            if n != viewer
        ]
        if viewer is None:
            lines[1] = "Scouts: " + "; ".join(scouts) + "."
        elif scouts:
            lines.insert(2, "Other scouts: " + "; ".join(scouts) + ".")
        if self.claims:
            claimed = (f"scout {n} → {r} {d}" for n, (r, d) in sorted(self.claims.items()))
            lines.append("Claims: " + "; ".join(claimed) + ".")
        return "\n".join(lines)


@dataclass
class ScoutState:
    number: int
    tool_node: ToolNode
    start: str  # its start room JSON, shown on its first turn
    view: SharedMap  # the map it is shown; the board itself on the blackboard
    task: str = ""
    steps_left: int | None = None  # None: no limit (blackboard)
    last_turn: list[BaseMessage] = field(default_factory=list)
    started: bool = False
    turns: int = 0  # model turns taken, for the blackboard's round robin
    done: bool = False
    report: str = ""  # its answer when it finished the task
    failed: str = ""  # its last failed tool call in this task, for A8's round report


def _gather(old: list[Any], new: list[Any]) -> list[Any]:
    return old + new if new else []  # `act` writes [] to clear the turn's replies


class ScoutGraph(TypedDict):
    scouts: list[ScoutState]
    replies: Annotated[list[tuple[int, AIMessage]], _gather]
    board: SharedMap | None  # the merged map, if the pattern keeps one
    steps: Annotated[int, operator.add]  # tool calls applied so far


class ScoutTurn(TypedDict):
    number: int
    messages: list[BaseMessage]


def scout_messages(kit: Kit, scout: ScoutState) -> list[BaseMessage]:
    system = SystemMessage(f"{kit.base_prompt}\n\n{MAP_INSTRUCTIONS} {SCOUT_INSTRUCTIONS}")
    task = f"You are scout {scout.number}. Your task: {scout.task}"
    if not scout.started:
        task += "\n\n" + scout.start
    return [
        system,
        HumanMessage(task),
        *scout.last_turn,
        HumanMessage(scout.view.render(scout.number)),
    ]


def dispatch(kit: Kit, after: str) -> Callable[[ScoutGraph], Sequence[Send] | str]:
    """A conditional edge: a Send per active scout, or `after` when none is left."""

    def edge(state: ScoutGraph) -> Sequence[Send] | str:
        active = [s for s in state["scouts"] if not s.done]
        if not active:
            return after
        return [
            Send("scout", ScoutTurn(number=s.number, messages=scout_messages(kit, s)))
            for s in active
        ]

    return edge


class ScoutNode(Protocol):
    """A graph node; the parameter is named `state` so that `StateGraph.add_node` accepts it."""

    def __call__(self, state: ScoutTurn) -> dict[str, Any]: ...


def scout_node(kit: Kit) -> ScoutNode:
    model = kit.model.bind_tools(kit.tools)

    def scout(state: ScoutTurn) -> dict[str, Any]:
        config: Any = {"metadata": {"role": f"scout {state['number']}"}}
        reply = model.invoke(state["messages"], config=config)
        assert isinstance(reply, AIMessage)
        return {"replies": [(state["number"], reply)]}

    return scout


def act(state: ScoutGraph) -> dict[str, Any]:
    """Applies the turn's tool calls in scout order, all of one scout's before the next."""
    by_number = {s.number: s for s in state["scouts"]}
    applied = 0
    for number, reply in sorted(state["replies"], key=lambda r: r[0]):
        scout = by_number[number]
        scout.started = True
        scout.turns += 1
        if match := _CLAIM.search(str(reply.text)):
            if state["board"] is not None:
                state["board"].claims[number] = (match[1], match[2])
        calls = [*reply.tool_calls, *reply.invalid_tool_calls]
        if not calls:
            scout.done, scout.report, scout.last_turn = True, str(reply.text), [reply]
            continue
        if scout.steps_left is not None and len(calls) > scout.steps_left:
            # Only the calls within its limit run; the reply is cut to match its results.
            kept = {c["id"] for c in calls[: scout.steps_left]}
            reply = reply.model_copy(
                update={
                    "tool_calls": [c for c in reply.tool_calls if c["id"] in kept],
                    "invalid_tool_calls": [c for c in reply.invalid_tool_calls if c["id"] in kept],
                }
            )
            calls = [c for c in calls if c["id"] in kept]
        results = scout.tool_node({"messages": [reply]})["messages"]
        by_id = {c["id"]: c for c in calls}
        for result in results:
            call = by_id[result.tool_call_id]
            args = call["args"] if isinstance(call["args"], dict) else {}
            data = json.loads(str(result.content))
            if not data["ok"]:
                shown = json.dumps(args)
                scout.failed = f"{call['name']} {shown}: {data['error']['message']}"
            for board in {id(m): m for m in (scout.view, state["board"]) if m is not None}.values():
                board.apply(number, call["name"] or "", args, data)
        applied += len(results)
        scout.last_turn = [reply, *results]
        if scout.steps_left is not None:
            scout.steps_left -= len(results)
            if scout.steps_left <= 0:
                scout.done = True
    return {"scouts": state["scouts"], "replies": [], "steps": applied}


def round_view(board: SharedMap) -> SharedMap:
    """A copy of the board for one round: the scout's own results go on top of it."""
    return copy.deepcopy(board)


def read_answer(text: str) -> dict[str, Any] | str:
    """The JSON object in an orchestrator's reply, or why there is none (research R9)."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return "the answer has no JSON object"
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as error:
        return f"the JSON does not parse ({error.msg})"
    return data if isinstance(data, dict) else "the answer must be one JSON object"


def read_tasks(
    data: dict[str, Any], key: str, with_scout: bool
) -> list[tuple[int | None, str, int]] | str:
    """The (scout, task, steps) entries of an answer, or what is wrong with them."""
    entries = data.get(key)
    if not isinstance(entries, list) or not entries:
        return f'"{key}" must be a list with at least one entry'
    if len(entries) > 4:
        return f'"{key}" may have at most 4 entries'
    found: list[tuple[int | None, str, int]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            return f"each entry of {key!r} must be an object"
        scout, task, steps = entry.get("scout"), entry.get("task"), entry.get("steps")
        if with_scout and (
            not isinstance(scout, int) or isinstance(scout, bool) or not 0 <= scout <= 3
        ):
            return f"scout {scout} is not a scout number from 0 to 3"
        if not isinstance(task, str) or not task.strip():
            return "every entry needs a task text"
        if not isinstance(steps, int) or isinstance(steps, bool) or steps < 1:
            return "every entry needs a whole number of steps of at least 1"
        found.append((scout if with_scout else None, task.strip(), steps))
    if with_scout and len({s for s, _, _ in found}) < len(found):
        return "each scout may get only one task per round"
    return found


def new_scout(kit: Kit, view: Callable[[int, str], SharedMap]) -> ScoutState | None:
    """A scout from `kit.add_scout()`, with the map `view(number, start)` gives it."""
    added = kit.add_scout()
    if added is None:
        return None
    return ScoutState(added.number, added.tool_node, added.start, view(added.number, added.start))


def first_scout(kit: Kit, view: Callable[[int, str], SharedMap]) -> ScoutState:
    return ScoutState(0, kit.tool_node, kit.start, view(0, kit.start))
