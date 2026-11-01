"""One episode on one survey field: scouts, steps, budget, log. Runner side only.

Architectures get an `AgentTools` (apl.survey.tools) wrapping an Episode, never the Episode.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from apl.survey.model import DIRECTIONS, Action, Cell, Field, cell_name
from apl.survey.results import CellView, EndReason, ErrorCode, Submitted, ToolResult

MAX_SCOUTS = 4  # per episode, scout 0 included, as on the dungeon
MAX_ATTEMPTS = 3  # for a retrying architecture, as on the dungeon (specs/007)


@dataclass(frozen=True, slots=True)
class LogEntry:
    index: int
    step: int | None  # None for uncounted episode_over calls
    action: Action
    result: ToolResult
    scout: int = 0
    turn: int | None = None  # the model call count when the call was applied (research R11)
    attempt: int = 1  # specs/007

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "step": self.step,
            **({"scout": self.scout} if self.scout else {}),
            **({"turn": self.turn} if self.turn is not None else {}),
            **({"attempt": self.attempt} if self.attempt > 1 else {}),
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
    submitted_total: int | None
    true_total: int
    cells_seen: int
    cells: int
    reference_is_optimal: bool
    attempts: int = 1  # the attempt the episode ended in (specs/007)

    @property
    def scouts(self) -> int:
        """Scouts that made at least one tool call."""
        return len({e.scout for e in self.log})

    @property
    def success(self) -> bool:
        return self.end_reason == EndReason.SUBMITTED and self.submitted_total == self.true_total

    @property
    def budget_hit(self) -> bool:
        return self.end_reason == EndReason.BUDGET

    @property
    def parallel_turns(self) -> int:
        """Groups of calls between model calls; one per step without a turn source (R11)."""
        counted = [e for e in self.log if e.step is not None]
        if any(e.turn is None for e in counted):
            return len(counted)
        return len({e.turn for e in counted})

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
            "submitted_total": self.submitted_total,
            "true_total": self.true_total,
            "cells_seen": self.cells_seen,
            "cells": self.cells,
            "parallel_turns": self.parallel_turns,
            "reference_is_optimal": self.reference_is_optimal,
            **({"attempts": self.attempts} if self.attempts > 1 else {}),
            "log": [e.to_dict() for e in self.log],
        }


def start_episode(field: Field) -> Episode:
    return Episode(field)


def _total(raw: object) -> int | None:
    # A JSON integer, or a string of digits (models sometimes quote numbers); research R7.
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw >= 0 else None
    if isinstance(raw, str) and raw.isascii() and raw.isdigit():
        return int(raw)
    return None


class Episode:
    def __init__(self, field: Field) -> None:
        self.field = field
        self.scouts: list[Cell] = [field.start]
        self.seen: set[Cell] = {field.start}  # in this attempt
        self.seen_ever: set[Cell] = {field.start}  # in every attempt, for the outcome
        self.steps = 0
        self.invalid_actions = 0
        self.submitted: int | None = None
        self.end_reason: EndReason | None = None
        self.log: list[LogEntry] = []
        self.on_step: Callable[[LogEntry], None] | None = None  # an observer, e.g. the viewer
        self.turn_source: Callable[[], int] | None = None  # set by the runner (research R11)
        self.attempt = 1
        self.max_attempts = 1  # MAX_ATTEMPTS for a retrying architecture (specs/007 R2)
        self.on_restart: Callable[[], None] | None = None  # an observer, e.g. the viewer

    def add_scout(self) -> int | None:
        """A new scout at the start; None once there are MAX_SCOUTS. Costs no step."""
        if len(self.scouts) >= MAX_SCOUTS:
            return None
        self.scouts.append(self.field.start)
        return len(self.scouts) - 1

    def restart(self) -> bool:
        """The field back in its start state for the next attempt; steps and log go on.

        Costs no step. Refused once the episode is over or the attempts are used up.
        """
        if self.end_reason is not None or self.attempt >= self.max_attempts:
            return False
        self.scouts = [self.field.start]
        self.seen = {self.field.start}
        self.submitted = None
        self.attempt += 1
        if self.on_restart is not None:
            self.on_restart()
        return True

    def describe(self, scout: int = 0) -> CellView:
        """A scout's cell, as it sees it. Free: does not count as a step."""
        here = self.scouts[self._scout(scout)]
        return CellView(
            cell=cell_name(here),
            deposit=here in self.field.deposits,
            exits=self.field.exits(here),
            columns=self.field.size,
            rows=self.field.size,
        )

    def look(self, scout: int = 0) -> ToolResult:
        return self._call(scout, Action("look"), lambda: ToolResult.success(self.describe(scout)))

    def move(self, direction: object, scout: int = 0) -> ToolResult:
        shown = direction if isinstance(direction, str) else repr(direction)
        return self._call(scout, Action("move", (shown,)), lambda: self._move(direction, scout))

    def submit(self, total: object, scout: int = 0) -> ToolResult:
        shown = total if isinstance(total, str) else repr(total)
        return self._call(scout, Action("submit", (shown,)), lambda: self._submit(total))

    def unknown(self, name: str, scout: int = 0) -> ToolResult:
        """A call to a tool that does not exist. It still costs a step (Constitution III)."""
        message = f"There is no tool named {name!r}. The tools are look, move and submit."
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
        f = self.field
        return Outcome(
            level=f.level.name if f.level else None,
            seed=f.seed,
            end_reason=self.end_reason,
            steps=self.steps,
            optimal_steps=f.reference_steps,
            budget=f.budget,
            invalid_actions=self.invalid_actions,
            log=tuple(self.log),
            submitted_total=self.submitted,
            true_total=f.true_total,
            cells_seen=len(self.seen_ever),
            cells=f.cells,
            reference_is_optimal=f.reference_is_optimal,
            attempts=self.attempt,
        )

    def _scout(self, number: int) -> int:
        if not 0 <= number < len(self.scouts):
            raise ValueError(f"there is no scout {number} (scouts: {len(self.scouts)})")
        return number

    def _call(self, scout: int, action: Action, handler: Callable[[], ToolResult]) -> ToolResult:
        self._scout(scout)
        turn = self.turn_source() if self.turn_source is not None else None
        if self.end_reason is not None:
            result = ToolResult.failure(ErrorCode.EPISODE_OVER, "The episode is over.")
            self._append(LogEntry(len(self.log), None, action, result, scout, turn, self.attempt))
            return result
        self.steps += 1
        attempt = self.attempt
        result = handler()
        if not result.ok:
            self.invalid_actions += 1
        retry = self.submitted is not None and self._retries_wrong_total()
        # A submission on the last step counts before the budget.
        if self.submitted is not None and not retry:
            self.end_reason = EndReason.SUBMITTED
        elif self.steps >= self.field.budget:
            self.end_reason = EndReason.BUDGET
        if retry and self.end_reason is None:
            # A wrong total ends a retrying architecture's attempt (specs/007 research R3).
            result = ToolResult.success(
                Submitted(self.submitted or 0, False, self.max_attempts - self.attempt)
            )
        self._append(LogEntry(len(self.log), self.steps, action, result, scout, turn, attempt))
        if retry and self.end_reason is None:
            self.restart()
        return result

    def _retries_wrong_total(self) -> bool:
        return self.submitted != self.field.true_total and self.attempt < self.max_attempts

    def _append(self, entry: LogEntry) -> None:
        self.log.append(entry)
        if self.on_step is not None:
            self.on_step(entry)

    def _move(self, raw: object, scout: int) -> ToolResult:
        if not isinstance(raw, str) or raw not in DIRECTIONS:
            return ToolResult.failure(
                ErrorCode.INVALID_DIRECTION,
                f"{raw!r} is not a direction; use north, east, south or west.",
            )
        other = self.field.neighbor(self.scouts[scout], raw)
        if other is None:
            return ToolResult.failure(ErrorCode.WALL, f"There is a wall to the {raw}.")
        self.scouts[scout] = other
        self.seen.add(other)
        self.seen_ever.add(other)
        return ToolResult.success(self.describe(scout))

    def _submit(self, raw: object) -> ToolResult:
        total = _total(raw)
        if total is None:
            return ToolResult.failure(
                ErrorCode.INVALID_TOTAL, f"{raw!r} is not a whole number of deposits."
            )
        self.submitted = total
        return ToolResult.success(Submitted(total))
