"""One episode on one dungeon: state, step counting, budget, log. Runner side only.

Architectures get an `AgentTools` (apl.dungeon.tools) wrapping an Episode, never the Episode.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from apl.dungeon.model import Action, Direction, Dungeon, Edge, Pos, key_name
from apl.dungeon.results import (
    DoorOpened,
    EndReason,
    ErrorCode,
    ExitView,
    InventoryView,
    RoomView,
    ToolResult,
)

MAX_SCOUTS = 4  # per episode, scout 0 included (specs/004 research R1)


@dataclass(frozen=True, slots=True)
class LogEntry:
    index: int
    step: int | None  # None for uncounted episode_over calls
    action: Action
    result: ToolResult
    scout: int = 0

    def to_dict(self) -> dict[str, object]:
        # "scout" only when it says something, so single-agent logs stay as they were.
        return {
            "index": self.index,
            "step": self.step,
            **({"scout": self.scout} if self.scout else {}),
            "action": self.action.to_dict(),
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class Outcome:
    level: str | None
    seed: int | None
    end_reason: EndReason
    steps: int
    optimal_steps: int
    budget: int
    invalid_actions: int
    log: tuple[LogEntry, ...]

    @property
    def scouts(self) -> int:
        """Scouts that made at least one tool call."""
        return len({e.scout for e in self.log})

    @property
    def success(self) -> bool:
        return self.end_reason == EndReason.EXIT

    @property
    def budget_hit(self) -> bool:
        return self.end_reason == EndReason.BUDGET

    def to_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "seed": self.seed,
            "success": self.success,
            "end_reason": str(self.end_reason),
            "steps": self.steps,
            "optimal_steps": self.optimal_steps,
            "budget": self.budget,
            "invalid_actions": self.invalid_actions,
            "budget_hit": self.budget_hit,
            **({"scouts": self.scouts} if self.scouts > 1 else {}),
            "log": [e.to_dict() for e in self.log],
        }


def start_episode(dungeon: Dungeon) -> Episode:
    return Episode(dungeon)


def _direction(raw: object) -> Direction | None:
    # Tool arguments come from a model, so they may not even be strings.
    return Direction(raw) if isinstance(raw, str) and raw in set(Direction) else None


@dataclass(slots=True)
class Scout:
    """One body in the dungeon. Single-agent architectures have only scout 0."""

    position: Pos
    inventory: list[str]  # key colors, in pick-up order


class Episode:
    def __init__(self, dungeon: Dungeon) -> None:
        self.dungeon = dungeon
        self.scouts = [Scout(dungeon.layout.start, [])]
        self._acting = 0  # the scout of the call being handled
        self.opened: set[Edge] = set()
        self.steps = 0
        self.invalid_actions = 0
        self.end_reason: EndReason | None = None
        self.log: list[LogEntry] = []
        self.on_step: Callable[[LogEntry], None] | None = None  # an observer, e.g. the viewer

    # The acting scout's body; scout 0's outside a call, for everything that knows one agent.
    @property
    def position(self) -> Pos:
        return self.scouts[self._acting].position

    @position.setter
    def position(self, value: Pos) -> None:
        self.scouts[self._acting].position = value

    @property
    def inventory(self) -> list[str]:
        return self.scouts[self._acting].inventory

    @property
    def keys_in_rooms(self) -> dict[str, Pos]:
        held = {c for s in self.scouts for c in s.inventory}
        return {c: p for c, p in sorted(self.dungeon.layout.keys.items()) if c not in held}

    def add_scout(self) -> int | None:
        """A new scout in the start room; None once there are MAX_SCOUTS. Costs no step."""
        if len(self.scouts) >= MAX_SCOUTS:
            return None
        self.scouts.append(Scout(self.dungeon.layout.start, []))
        return len(self.scouts) - 1

    def describe(self, scout: int = 0) -> RoomView:
        """A scout's room, as it sees it. Free: does not count as a step."""
        body = self._scout(scout)
        layout = self.dungeon.layout
        exits = []
        for direction in Direction:
            edge = layout.door(body.position, direction)
            if edge is not None:
                lock = layout.locks.get(edge) if edge not in self.opened else None
                exits.append(ExitView(direction, lock))
        here = body.position
        return RoomView(
            label=layout.labels[here],
            exits=tuple(exits),
            items=tuple(key_name(c) for c, p in self.keys_in_rooms.items() if p == here),
            inventory=tuple(key_name(c) for c in body.inventory),
            is_exit=here == layout.exit,
        )

    def look(self, scout: int = 0) -> ToolResult:
        return self._call(scout, Action("look"), lambda: ToolResult.success(self.describe(scout)))

    def move(self, direction: str, scout: int = 0) -> ToolResult:
        return self._call(scout, Action("move", (direction,)), lambda: self._move(direction))

    def take(self, item: str, scout: int = 0) -> ToolResult:
        return self._call(scout, Action("take", (item,)), lambda: self._take(item))

    def use(self, item: str, direction: str, scout: int = 0) -> ToolResult:
        action = Action("use", (item, direction))
        return self._call(scout, action, lambda: self._use(item, direction))

    def unknown(self, name: str, scout: int = 0) -> ToolResult:
        """A call to a tool that does not exist. It still costs a step (Constitution III)."""
        message = f"There is no tool named {name!r}. The tools are look, move, take and use."
        return self._call(
            scout,
            Action("unknown", (name,)),
            lambda: ToolResult.failure(ErrorCode.UNKNOWN_TOOL, message),
        )

    def stop(self) -> None:
        """End the episode early (the architecture gave up). Costs no step."""
        if self.end_reason is None:
            self.end_reason = EndReason.STOPPED

    def outcome(self) -> Outcome:
        if self.end_reason is None:
            raise RuntimeError("the episode has not ended")
        d = self.dungeon
        return Outcome(
            level=d.level.name if d.level else None,
            seed=d.seed,
            end_reason=self.end_reason,
            steps=self.steps,
            optimal_steps=d.solution.length,
            budget=d.budget,
            invalid_actions=self.invalid_actions,
            log=tuple(self.log),
        )

    def _scout(self, number: int) -> Scout:
        if not 0 <= number < len(self.scouts):
            raise ValueError(f"there is no scout {number} (scouts: {len(self.scouts)})")
        return self.scouts[number]

    def _call(self, scout: int, action: Action, handler: Callable[[], ToolResult]) -> ToolResult:
        self._scout(scout)
        if self.end_reason is not None:
            result = ToolResult.failure(ErrorCode.EPISODE_OVER, "The episode is over.")
            self._append(LogEntry(len(self.log), None, action, result, scout))
            return result
        self.steps += 1
        self._acting = scout
        try:
            result = handler()
            # Exit before budget: reaching the exit on the last step is a success.
            at_exit = self.position == self.dungeon.layout.exit
        finally:
            self._acting = 0
        if not result.ok:
            self.invalid_actions += 1
        if at_exit:
            self.end_reason = EndReason.EXIT
        elif self.steps >= self.dungeon.budget:
            self.end_reason = EndReason.BUDGET
        self._append(LogEntry(len(self.log), self.steps, action, result, scout))
        return result

    def _append(self, entry: LogEntry) -> None:
        self.log.append(entry)
        if self.on_step is not None:
            self.on_step(entry)

    def _door(self, raw: object) -> tuple[Direction, Edge] | ToolResult:
        direction = _direction(raw)
        if direction is None:
            return ToolResult.failure(
                ErrorCode.INVALID_DIRECTION,
                f"{raw!r} is not a direction; use north, east, south or west.",
            )
        edge = self.dungeon.layout.door(self.position, direction)
        if edge is None:
            return ToolResult.failure(ErrorCode.NO_DOOR, f"There is no door to the {direction}.")
        return direction, edge

    def _move(self, raw: str) -> ToolResult:
        door = self._door(raw)
        if isinstance(door, ToolResult):
            return door
        direction, edge = door
        color = self.dungeon.layout.locks.get(edge)
        if color is not None and edge not in self.opened:
            return ToolResult.failure(
                ErrorCode.LOCKED, f"The door to the {direction} is locked ({color})."
            )
        self.position = edge.other(self.position)
        return ToolResult.success(self.describe(self._acting))

    def _take(self, item: str) -> ToolResult:
        for color, pos in self.keys_in_rooms.items():
            if pos == self.position and item == key_name(color):
                self.inventory.append(color)
                return ToolResult.success(InventoryView(tuple(key_name(c) for c in self.inventory)))
        return ToolResult.failure(ErrorCode.NO_SUCH_ITEM, f"There is no {item!r} here.")

    def _use(self, item: str, raw: str) -> ToolResult:
        door = self._door(raw)
        if isinstance(door, ToolResult):
            return door
        direction, edge = door
        if item not in (key_name(c) for c in self.inventory):
            return ToolResult.failure(ErrorCode.NOT_IN_INVENTORY, f"You do not hold {item!r}.")
        color = self.dungeon.layout.locks.get(edge)
        if color is None:
            return ToolResult.failure(
                ErrorCode.NOT_LOCKED, f"The door to the {direction} is not locked."
            )
        if item != key_name(color):
            return ToolResult.failure(
                ErrorCode.WRONG_KEY, f"The {item} does not fit the {color} lock."
            )
        if edge in self.opened:
            return ToolResult.failure(
                ErrorCode.NOT_LOCKED, f"The door to the {direction} is already open."
            )
        self.opened.add(edge)
        return ToolResult.success(DoorOpened(direction, color))
