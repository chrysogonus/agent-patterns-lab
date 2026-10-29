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


@dataclass(frozen=True, slots=True)
class LogEntry:
    index: int
    step: int | None  # None for uncounted episode_over calls
    action: Action
    result: ToolResult

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "step": self.step,
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
            "log": [e.to_dict() for e in self.log],
        }


def start_episode(dungeon: Dungeon) -> Episode:
    return Episode(dungeon)


def _direction(raw: object) -> Direction | None:
    # Tool arguments come from a model, so they may not even be strings.
    return Direction(raw) if isinstance(raw, str) and raw in set(Direction) else None


class Episode:
    def __init__(self, dungeon: Dungeon) -> None:
        self.dungeon = dungeon
        self.position: Pos = dungeon.layout.start
        self.inventory: list[str] = []  # key colors, in pick-up order
        self.opened: set[Edge] = set()
        self.steps = 0
        self.invalid_actions = 0
        self.end_reason: EndReason | None = None
        self.log: list[LogEntry] = []

    @property
    def keys_in_rooms(self) -> dict[str, Pos]:
        return {
            c: p for c, p in sorted(self.dungeon.layout.keys.items()) if c not in self.inventory
        }

    def describe(self) -> RoomView:
        """The current room, as the agent sees it. Free: does not count as a step."""
        layout = self.dungeon.layout
        exits = []
        for direction in Direction:
            edge = layout.door(self.position, direction)
            if edge is not None:
                lock = layout.locks.get(edge) if edge not in self.opened else None
                exits.append(ExitView(direction, lock))
        return RoomView(
            label=layout.labels[self.position],
            exits=tuple(exits),
            items=tuple(key_name(c) for c, p in self.keys_in_rooms.items() if p == self.position),
            inventory=tuple(key_name(c) for c in self.inventory),
            is_exit=self.position == layout.exit,
        )

    def look(self) -> ToolResult:
        return self._call(Action("look"), lambda: ToolResult.success(self.describe()))

    def move(self, direction: str) -> ToolResult:
        return self._call(Action("move", (direction,)), lambda: self._move(direction))

    def take(self, item: str) -> ToolResult:
        return self._call(Action("take", (item,)), lambda: self._take(item))

    def use(self, item: str, direction: str) -> ToolResult:
        return self._call(Action("use", (item, direction)), lambda: self._use(item, direction))

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

    def _call(self, action: Action, handler: Callable[[], ToolResult]) -> ToolResult:
        if self.end_reason is not None:
            result = ToolResult.failure(ErrorCode.EPISODE_OVER, "The episode is over.")
            self.log.append(LogEntry(len(self.log), None, action, result))
            return result
        self.steps += 1
        result = handler()
        if not result.ok:
            self.invalid_actions += 1
        # Exit before budget: reaching the exit on the last step is a success.
        if self.position == self.dungeon.layout.exit:
            self.end_reason = EndReason.EXIT
        elif self.steps >= self.dungeon.budget:
            self.end_reason = EndReason.BUDGET
        self.log.append(LogEntry(len(self.log), self.steps, action, result))
        return result

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
        return ToolResult.success(self.describe())

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
