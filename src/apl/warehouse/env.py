"""One episode in one warehouse: robots, packages, steps, budget, log. Runner side only.

Architectures get an `AgentTools` (apl.warehouse.tools) wrapping an Episode, never the Episode.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from apl.warehouse.model import DIRECTIONS, STEP, Action, Cell, Floor, cell_name
from apl.warehouse.results import (
    Dropped,
    EndReason,
    ErrorCode,
    Picked,
    RobotView,
    StartView,
    ToolResult,
)

MAX_SCOUTS = 4  # robots per episode, robot 0 included, as the other problems' scouts
MAX_ATTEMPTS = 1  # no retrying architecture plays the warehouse (research R4)


@dataclass(frozen=True, slots=True)
class LogEntry:
    index: int
    step: int | None  # None for uncounted episode_over calls
    action: Action
    result: ToolResult
    scout: int = 0
    turn: int | None = None  # the model call count when the call was applied (research R8)
    attempt: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "step": self.step,
            **({"scout": self.scout} if self.scout else {}),
            **({"turn": self.turn} if self.turn is not None else {}),
            "action": self.action.to_dict(),
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class Outcome:
    level: str | None
    seed: int | None
    end_reason: EndReason
    steps: int
    optimal_steps: int  # the reference steps
    budget: int
    invalid_actions: int
    log: tuple[LogEntry, ...]
    delivered: int
    packages: int
    added_turns: tuple[int, ...]  # the turn each robot was added at (research R8)
    reference_is_optimal: bool = False
    attempts: int = 1

    @property
    def scouts(self) -> int:
        """Robots that made at least one tool call."""
        return len({e.scout for e in self.log})

    @property
    def success(self) -> bool:
        return self.end_reason == EndReason.DELIVERED

    @property
    def budget_hit(self) -> bool:
        return self.end_reason == EndReason.BUDGET

    def _turns(self) -> dict[int, set[int]]:
        """The robots that made a counted call, per parallel turn (one per call without turns)."""
        counted = [e for e in self.log if e.step is not None]
        timed = all(e.turn is not None for e in counted)
        found: dict[int, set[int]] = {}
        for e in counted:
            key = e.turn if timed and e.turn is not None else e.step or 0
            found.setdefault(key, set()).add(e.scout)
        return found

    @property
    def parallel_turns(self) -> int:
        return len(self._turns())

    @property
    def idle_robot_turns(self) -> int:
        """Per parallel turn, the robots already added that made no call in it."""
        return sum(
            sum(1 for a in self.added_turns if a <= turn) - len(acting)
            for turn, acting in self._turns().items()
        )

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
            "delivered": self.delivered,
            "packages": self.packages,
            "parallel_turns": self.parallel_turns,
            "idle_robot_turns": self.idle_robot_turns,
            "added_turns": list(self.added_turns),
            "reference_is_optimal": self.reference_is_optimal,
            "log": [e.to_dict() for e in self.log],
        }


def start_episode(floor: Floor) -> Episode:
    return Episode(floor)


class Episode:
    def __init__(self, floor: Floor) -> None:
        self.floor = floor
        self.robots: list[Cell] = [floor.dock]
        self.carrying: list[str | None] = [None]
        self.added_turn: list[int] = [0]
        self.waiting: dict[str, Cell] = dict(floor.packages)
        self.delivered: list[str] = []
        self.seen: set[Cell] = set(self._sight(floor.dock))
        self.steps = 0
        self.invalid_actions = 0
        self.end_reason: EndReason | None = None
        self.log: list[LogEntry] = []
        self.on_step: Callable[[LogEntry], None] | None = None  # an observer, e.g. the viewer
        self.turn_source: Callable[[], int] | None = None  # set by the runner (research R8)
        self.attempt = 1
        self.max_attempts = MAX_ATTEMPTS
        self.on_restart: Callable[[], None] | None = None

    def add_scout(self) -> int | None:
        """A new robot on the dock; None once there are MAX_SCOUTS. Costs no step."""
        if len(self.robots) >= MAX_SCOUTS:
            return None
        self.robots.append(self.floor.dock)
        self.carrying.append(None)
        self.added_turn.append(self.turn_source() if self.turn_source is not None else 0)
        return len(self.robots) - 1

    def restart(self) -> bool:
        """No retrying architecture plays the warehouse: always refused."""
        return False

    def describe(self, robot: int = 0) -> RobotView:
        """A robot's view. Free: does not count as a step."""
        here = self.robots[self._robot(robot)]
        visible = set(self._sight(here))
        seen = sorted(
            ((name, cell) for name, cell in self.waiting.items() if cell in visible),
            key=lambda p: (p[1][1], p[1][0]),
        )
        return RobotView(
            cell=cell_name(here),
            corridors=self.floor.corridors(here),
            packages_seen=tuple((name, cell_name(cell)) for name, cell in seen),
            carrying=self.carrying[robot],
            on_drop=here == self.floor.drop,
            delivered=len(self.delivered),
            packages=len(self.floor.packages),
            columns=self.floor.columns,
            rows=self.floor.rows,
        )

    def start_view(self, robot: int = 0) -> StartView:
        return StartView(self.describe(robot), self.floor.plan(), self.floor.aisle_names)

    def look(self, scout: int = 0) -> ToolResult:
        return self._call(scout, Action("look"), lambda: ToolResult.success(self.describe(scout)))

    def move(self, direction: object, scout: int = 0) -> ToolResult:
        shown = direction if isinstance(direction, str) else repr(direction)
        return self._call(scout, Action("move", (shown,)), lambda: self._move(direction, scout))

    def pick(self, scout: int = 0) -> ToolResult:
        return self._call(scout, Action("pick"), lambda: self._pick(scout))

    def drop(self, scout: int = 0) -> ToolResult:
        return self._call(scout, Action("drop"), lambda: self._drop(scout))

    def unknown(self, name: str, scout: int = 0) -> ToolResult:
        """A call to a tool that does not exist. It still costs a step (Constitution III)."""
        message = f"There is no tool named {name!r}. The tools are look, move, pick and drop."
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
        f = self.floor
        return Outcome(
            level=f.level.name if f.level else None,
            seed=f.seed,
            end_reason=self.end_reason,
            steps=self.steps,
            optimal_steps=f.reference_steps,
            budget=f.budget,
            invalid_actions=self.invalid_actions,
            log=tuple(self.log),
            delivered=len(self.delivered),
            packages=len(f.packages),
            added_turns=tuple(self.added_turn),
            reference_is_optimal=f.reference_is_optimal,
        )

    def _sight(self, cell: Cell) -> list[Cell]:
        return [c for name in self.floor.corridors(cell) for c in self.floor.corridor_cells(name)]

    def _robot(self, number: int) -> int:
        if not 0 <= number < len(self.robots):
            raise ValueError(f"there is no robot {number} (robots: {len(self.robots)})")
        return number

    def _call(self, scout: int, action: Action, handler: Callable[[], ToolResult]) -> ToolResult:
        self._robot(scout)
        turn = self.turn_source() if self.turn_source is not None else None
        if self.end_reason is not None:
            result = ToolResult.failure(ErrorCode.EPISODE_OVER, "The episode is over.")
            self._append(LogEntry(len(self.log), None, action, result, scout, turn))
            return result
        self.steps += 1
        result = handler()
        if not result.ok:
            self.invalid_actions += 1
        # The last delivery on the last step counts before the budget.
        if len(self.delivered) == len(self.floor.packages):
            self.end_reason = EndReason.DELIVERED
        elif self.steps >= self.floor.budget:
            self.end_reason = EndReason.BUDGET
        self._append(LogEntry(len(self.log), self.steps, action, result, scout, turn))
        return result

    def _append(self, entry: LogEntry) -> None:
        self.log.append(entry)
        if self.on_step is not None:
            self.on_step(entry)

    def _move(self, raw: object, robot: int) -> ToolResult:
        if not isinstance(raw, str) or raw not in DIRECTIONS:
            return ToolResult.failure(
                ErrorCode.INVALID_DIRECTION,
                f"{raw!r} is not a direction; use north, east, south or west.",
            )
        here = self.robots[robot]
        other = self.floor.neighbor(here, raw)
        if other is None:
            dx, dy = STEP[raw]
            if self.floor.inside((here[0] + dx, here[1] + dy)):
                return ToolResult.failure(ErrorCode.SHELF, f"There is a shelf to the {raw}.")
            return ToolResult.failure(ErrorCode.EDGE, f"The floor ends to the {raw}.")
        self.robots[robot] = other
        self.seen.update(self._sight(other))
        return ToolResult.success(self.describe(robot))

    def _pick(self, robot: int) -> ToolResult:
        here = self.robots[robot]
        held = self.carrying[robot]
        if held is not None:
            return ToolResult.failure(ErrorCode.ALREADY_CARRYING, f"You already carry {held}.")
        found = next((name for name, cell in self.waiting.items() if cell == here), None)
        if found is None:
            return ToolResult.failure(
                ErrorCode.NO_PACKAGE, f"There is no package on {cell_name(here)}."
            )
        del self.waiting[found]
        self.carrying[robot] = found
        return ToolResult.success(Picked(found, cell_name(here)))

    def _drop(self, robot: int) -> ToolResult:
        held = self.carrying[robot]
        if held is None:
            return ToolResult.failure(ErrorCode.NOT_CARRYING, "You carry nothing.")
        if self.robots[robot] != self.floor.drop:
            return ToolResult.failure(ErrorCode.NOT_ON_DROP, "You can drop only on D.")
        self.carrying[robot] = None
        self.delivered.append(held)
        return ToolResult.success(Dropped(held, len(self.delivered), len(self.floor.packages)))
