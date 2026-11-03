"""One episode on one rune floor: steps, budget, walks, traps, attempts, log. Runner side only.

Architectures get an `AgentTools` (apl.rune.tools) wrapping an Episode, never the Episode.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from apl.rune.model import DIRECTIONS, Action, Cell, Floor, cell_name
from apl.rune.results import (
    EndReason,
    ErrorCode,
    FloorView,
    GoalView,
    StepView,
    ToolResult,
    TrapView,
)
from apl.rune.rules import next_state, outcome_of

MAX_ATTEMPTS = 3  # for a retrying architecture, as on the other problems (specs/007)


@dataclass(frozen=True, slots=True)
class LogEntry:
    index: int
    step: int | None  # None for uncounted episode_over calls
    action: Action
    result: ToolResult
    attempt: int = 1
    scout: int = 0  # one agent; the viewer reads it as on the other problems

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "step": self.step,
            **({"attempt": self.attempt} if self.attempt > 1 else {}),
            "action": self.action.to_dict(),
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class Trap:
    cell: Cell
    state: int  # the rule state it sprang in
    step: int
    attempt: int
    repeated: bool  # the same cell in the same state trapped before (research R8)


@dataclass(frozen=True, slots=True)
class Walk:
    """A finished walk: its cells in order and how it ended (trap, start or restart)."""

    cells: tuple[Cell, ...]
    ending: str
    at: Cell | None = None  # the trap's cell


@dataclass(frozen=True, slots=True)
class Outcome:
    level: str | None
    seed: int | None
    end_reason: EndReason
    steps: int
    optimal_steps: int  # the reference
    budget: int
    invalid_actions: int
    log: tuple[LogEntry, ...]
    traps: int
    repeated_traps: int
    walks: int
    reference_is_optimal: bool
    attempts: int = 1  # the attempt the episode ended in (specs/007)

    @property
    def scouts(self) -> int:
        return 1 if self.log else 0

    @property
    def success(self) -> bool:
        return self.end_reason == EndReason.GOAL

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
            "traps": self.traps,
            "repeated_traps": self.repeated_traps,
            "walks": self.walks,
            "reference_is_optimal": self.reference_is_optimal,
            **({"attempts": self.attempts} if self.attempts > 1 else {}),
            "log": [e.to_dict() for e in self.log],
        }


def start_episode(floor: Floor) -> Episode:
    return Episode(floor)


class Episode:
    def __init__(self, floor: Floor) -> None:
        self.floor = floor
        self.position = floor.start
        self.walk: list[Cell] = []  # the current walk's cells
        self.state = 0  # the rule state of the current walk
        self.finished: list[Walk] = []
        self.walks = 1  # walks started, the first included
        self.traps: list[Trap] = []
        self.repeated_traps = 0
        self._sprung: set[tuple[Cell, int]] = set()
        self.steps = 0
        self.invalid_actions = 0
        self.end_reason: EndReason | None = None
        self.log: list[LogEntry] = []
        self.on_step: Callable[[LogEntry], None] | None = None  # an observer, e.g. the viewer
        self.attempt = 1
        self.max_attempts = 1  # MAX_ATTEMPTS for a retrying architecture (specs/007 R2)
        self.on_restart: Callable[[], None] | None = None  # an observer, e.g. the viewer
        self._trapped = False  # set by the last move, for the retry rule

    def add_scout(self) -> int | None:
        """The rune floor has one agent (research R10)."""
        return None

    def restart(self) -> bool:
        """The agent back on the start for the next attempt; steps, traps and log go on.

        Costs no step. Refused once the episode is over or the attempts are used up.
        """
        if self.end_reason is not None or self.attempt >= self.max_attempts:
            return False
        if self.position != self.floor.start or self.walk:
            self._new_walk(Walk(tuple(self.walk), "restart"))
        self._next_attempt()
        return True

    def describe(self) -> FloorView:
        """The floor, as the agent sees it. Free: does not count as a step."""
        f = self.floor
        rows = tuple(tuple(f.word((x, y)) for x in range(f.columns)) for y in range(f.rows))
        return FloorView(
            f.columns, f.rows, cell_name(f.start), cell_name(f.goal), cell_name(self.position), rows
        )

    def look(self) -> ToolResult:
        return self._call(Action("look"), lambda: ToolResult.success(self.describe()))

    def move(self, raw: object) -> ToolResult:
        shown = raw if isinstance(raw, str) else repr(raw)
        return self._call(Action("move", (shown,)), lambda: self._move(raw))

    def unknown(self, name: str) -> ToolResult:
        """A call to a tool that does not exist. It still costs a step (Constitution III)."""
        message = f"There is no tool named {name!r}. The tools are look and move."
        return self._call(
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
            traps=len(self.traps),
            repeated_traps=self.repeated_traps,
            walks=self.walks,
            reference_is_optimal=f.reference_is_optimal,
            attempts=self.attempt,
        )

    def _call(self, action: Action, handler: Callable[[], ToolResult]) -> ToolResult:
        if self.end_reason is not None:
            result = ToolResult.failure(ErrorCode.EPISODE_OVER, "The episode is over.")
            self._append(LogEntry(len(self.log), None, action, result, self.attempt))
            return result
        self.steps += 1
        attempt = self.attempt
        self._trapped = False
        result = handler()
        if not result.ok:
            self.invalid_actions += 1
        # Reaching the goal on the last step counts before the budget.
        if isinstance(result.data, GoalView):
            self.end_reason = EndReason.GOAL
        elif self.steps >= self.floor.budget:
            self.end_reason = EndReason.BUDGET
        retry = self._trapped and self.end_reason is None and self.attempt < self.max_attempts
        if retry:
            # A trap ends a retrying architecture's attempt (research R10); the agent is on S.
            assert isinstance(result.data, TrapView)
            data = result.data
            left = self.max_attempts - self.attempt
            result = ToolResult.success(TrapView(data.trap, data.color, data.position, left))
        self._append(LogEntry(len(self.log), self.steps, action, result, attempt))
        if retry:
            self._next_attempt()  # after the step, as the signal trace's restart
        return result

    def _move(self, raw: object) -> ToolResult:
        if not isinstance(raw, str) or raw not in DIRECTIONS:
            return ToolResult.failure(
                ErrorCode.INVALID_DIRECTION,
                f"{raw!r} is not a direction; use north, east, south or west.",
            )
        other = self.floor.neighbor(self.position, raw)
        if other is None:
            return ToolResult.failure(
                ErrorCode.EDGE, f"There is no tile {raw} of {cell_name(self.position)}."
            )
        what = outcome_of(self.floor, self.state, other)
        if what == "goal":
            self.position = other  # the walk stays the current one: it reached the goal
            return ToolResult.success(GoalView(cell_name(other)))
        if what == "start":
            self._new_walk(Walk(tuple(self.walk), "start"))
            return ToolResult.success(StepView(cell_name(other), "start"))
        if what == "trap":
            key = (other, self.state)
            repeated = key in self._sprung
            self._sprung.add(key)
            self.repeated_traps += repeated
            self.traps.append(Trap(other, self.state, self.steps, self.attempt, repeated))
            self._new_walk(Walk(tuple(self.walk), "trap", other))
            self._trapped = True
            start = cell_name(self.floor.start)
            return ToolResult.success(TrapView(cell_name(other), self.floor.colors[other], start))
        self.position = other
        self.walk.append(other)
        self.state = next_state(self.floor.rule, self.state)
        return ToolResult.success(StepView(cell_name(other), self.floor.colors[other]))

    def _new_walk(self, ended: Walk) -> None:
        self.finished.append(ended)
        self.position = self.floor.start
        self.walk = []
        self.state = 0
        self.walks += 1

    def _next_attempt(self) -> None:
        self.attempt += 1
        if self.on_restart is not None:
            self.on_restart()

    def _append(self, entry: LogEntry) -> None:
        self.log.append(entry)
        if self.on_step is not None:
            self.on_step(entry)
