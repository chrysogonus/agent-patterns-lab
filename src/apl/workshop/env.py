"""One episode in one workshop: steps, budget, stock, inventory, attempts, log. Runner side only.

Architectures get an `AgentTools` (apl.workshop.tools) wrapping an Episode, never the Episode.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from apl.workshop.model import Action, Workshop
from apl.workshop.plans import feasible, reference_use
from apl.workshop.results import (
    CraftedView,
    EndReason,
    ErrorCode,
    GatheredView,
    RawView,
    RecipesView,
    StoreView,
    ToolResult,
)

MAX_ATTEMPTS = 3  # for a retrying architecture, as on the other problems (specs/007)


@dataclass(frozen=True, slots=True)
class LogEntry:
    index: int
    step: int | None  # None for uncounted episode_over calls
    action: Action
    result: ToolResult
    attempt: int = 1
    scout: int = 0  # one body; the viewer reads it as on the other problems

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "step": self.step,
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
    optimal_steps: int  # the reference
    budget: int
    invalid_actions: int
    log: tuple[LogEntry, ...]
    wasted: int
    inspected: int
    crafted: int
    reference_is_optimal: bool
    attempts: int = 1  # the attempt the episode ended in (specs/007)

    @property
    def scouts(self) -> int:
        return 1 if self.log else 0

    @property
    def success(self) -> bool:
        return self.end_reason == EndReason.GOAL

    @property
    def stuck(self) -> bool:
        return self.end_reason == EndReason.STUCK

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
            "stuck": self.stuck,
            "wasted": self.wasted,
            "inspected": self.inspected,
            "crafted": self.crafted,
            "reference_is_optimal": self.reference_is_optimal,
            **({"attempts": self.attempts} if self.attempts > 1 else {}),
            "log": [e.to_dict() for e in self.log],
        }


def start_episode(workshop: Workshop) -> Episode:
    return Episode(workshop)


def _recipe_number(raw: object) -> int | None:
    # A JSON integer, or a one-digit string (models sometimes quote numbers); research R9.
    if isinstance(raw, bool):
        return None
    if isinstance(raw, str) and raw.isascii() and raw.isdigit() and len(raw) == 1:
        raw = int(raw)
    return raw if isinstance(raw, int) else None


class Episode:
    def __init__(self, workshop: Workshop) -> None:
        self.workshop = workshop
        self.stock: dict[str, int] = dict(workshop.stock)
        self.inventory: dict[str, int] = {}
        self.inspected: list[str] = []  # in order, every attempt
        self.crafted = 0
        self.wasted = 0
        self._allowed = reference_use(workshop)
        self._used: dict[tuple[str, str], int] = {}  # this attempt's scarce use, by item
        self.steps = 0
        self.invalid_actions = 0
        self.end_reason: EndReason | None = None
        self.log: list[LogEntry] = []
        self.on_step: Callable[[LogEntry], None] | None = None  # an observer, e.g. the viewer
        self.attempt = 1
        self.max_attempts = 1  # MAX_ATTEMPTS for a retrying architecture (specs/007 R2)
        self.on_restart: Callable[[], None] | None = None  # an observer, e.g. the viewer
        self._stuck = False  # set by the last craft, for the end and retry rules

    def add_scout(self) -> int | None:
        """The workshop has one body (research R10)."""
        return None

    def restart(self) -> bool:
        """The workshop back in its start state for the next attempt; steps, waste and log go on.

        Costs no step. Refused once the episode is over or the attempts are used up.
        """
        if self.end_reason is not None or self.attempt >= self.max_attempts:
            return False
        self._next_attempt()
        return True

    def describe(self) -> StoreView:
        """The goal, the stock and the inventory, as the agent sees them. Free."""
        return StoreView(self.workshop.goal, tuple(self.stock.items()), self._held())

    def look(self) -> ToolResult:
        return self._call(Action("look"), lambda: ToolResult.success(self.describe()))

    def inspect(self, raw: object) -> ToolResult:
        return self._call(Action("inspect", (_shown(raw),)), lambda: self._inspect(raw))

    def gather(self, raw: object) -> ToolResult:
        return self._call(Action("gather", (_shown(raw),)), lambda: self._gather(raw))

    def craft(self, raw: object, recipe: object) -> ToolResult:
        action = Action("craft", (_shown(raw), _shown(recipe)))
        return self._call(action, lambda: self._craft(raw, recipe))

    def unknown(self, name: str) -> ToolResult:
        """A call to a tool that does not exist. It still costs a step (Constitution III)."""
        message = f"There is no tool named {name!r}. The tools are look, inspect, gather and craft."
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
        w = self.workshop
        return Outcome(
            level=w.level.name if w.level else None,
            seed=w.seed,
            end_reason=self.end_reason,
            steps=self.steps,
            optimal_steps=w.reference_steps,
            budget=w.budget,
            invalid_actions=self.invalid_actions,
            log=tuple(self.log),
            wasted=self.wasted,
            inspected=len(set(self.inspected)),
            crafted=self.crafted,
            reference_is_optimal=w.reference_is_optimal,
            attempts=self.attempt,
        )

    def _call(self, action: Action, handler: Callable[[], ToolResult]) -> ToolResult:
        if self.end_reason is not None:
            result = ToolResult.failure(ErrorCode.EPISODE_OVER, "The episode is over.")
            self._append(LogEntry(len(self.log), None, action, result, self.attempt))
            return result
        self.steps += 1
        attempt = self.attempt
        self._stuck = False
        result = handler()
        if not result.ok:
            self.invalid_actions += 1
        retry = False
        # Crafting the goal on the last step counts before the budget.
        if isinstance(result.data, CraftedView) and result.data.goal:
            self.end_reason = EndReason.GOAL
        elif self._stuck:
            retry = self.attempt < self.max_attempts and self.steps < self.workshop.budget
            if retry:
                # Getting stuck ends a retrying architecture's attempt (research R10).
                data = result.data
                assert isinstance(data, CraftedView)
                left = self.max_attempts - self.attempt
                result = ToolResult.success(
                    CraftedView(data.crafted, data.recipe, data.inventory, False, True, left)
                )
            else:
                self.end_reason = EndReason.STUCK
        elif self.steps >= self.workshop.budget:
            self.end_reason = EndReason.BUDGET
        self._append(LogEntry(len(self.log), self.steps, action, result, attempt))
        if retry:
            self._next_attempt()  # after the step, as the other problems' restarts
        return result

    def _unknown_item(self, raw: object) -> ToolResult:
        return ToolResult.failure(ErrorCode.UNKNOWN_ITEM, f"{raw!r} is not an item here.")

    def _inspect(self, raw: object) -> ToolResult:
        w = self.workshop
        if w.raw(raw):
            assert isinstance(raw, str)
            self.inspected.append(raw)
            return ToolResult.success(RawView(raw))
        if not w.craftable(raw):
            return self._unknown_item(raw)
        assert isinstance(raw, str)
        self.inspected.append(raw)
        return ToolResult.success(RecipesView(raw, tuple(w.recipes[raw])))

    def _gather(self, raw: object) -> ToolResult:
        w = self.workshop
        if w.craftable(raw):
            return ToolResult.failure(ErrorCode.NOT_RAW, f"{raw!r} is crafted, not gathered.")
        if not w.raw(raw):
            return self._unknown_item(raw)
        assert isinstance(raw, str)
        if self.stock[raw] == 0:
            return ToolResult.failure(
                ErrorCode.OUT_OF_STOCK, f"There is no {raw} left in the stock."
            )
        self.stock[raw] -= 1
        self.inventory[raw] = self.inventory.get(raw, 0) + 1
        return ToolResult.success(GatheredView(raw, self.stock[raw], self._held()))

    def _craft(self, raw: object, recipe: object) -> ToolResult:
        w = self.workshop
        if w.raw(raw):
            return ToolResult.failure(
                ErrorCode.NO_SUCH_RECIPE, f"{raw!r} is a raw material; gather it."
            )
        if not w.craftable(raw):
            return self._unknown_item(raw)
        assert isinstance(raw, str)
        recipes = w.recipes[raw]
        k = _recipe_number(recipe)
        # Before the item is inspected, an error says nothing of its recipes (FR-006).
        seen = raw in self.inspected
        if k is None or not 1 <= k <= len(recipes):
            has = f"{len(recipes)} recipe{'s' if len(recipes) > 1 else ''}"
            message = (
                f"{raw!r} has {has}; recipe {_shown(recipe)} does not exist."
                if seen
                else f"{raw!r} has no recipe {_shown(recipe)}."
            )
            return ToolResult.failure(ErrorCode.NO_SUCH_RECIPE, message)
        inputs = recipes[k - 1]
        need: dict[str, int] = {}
        for name in inputs:
            need[name] = need.get(name, 0) + 1
        missing = [n for n, c in need.items() if self.inventory.get(n, 0) < c]
        if missing:
            message = (
                f"Missing for {raw} (recipe {k}): {', '.join(missing)}."
                if seen
                else f"Missing inputs for {raw} (recipe {k})."
            )
            return ToolResult.failure(ErrorCode.MISSING_INPUTS, message)
        for name, count in need.items():
            self.inventory[name] -= count
            if self.inventory[name] == 0:
                del self.inventory[name]
            if name in w.scarce:
                key = (raw, name)
                for _ in range(count):
                    self._used[key] = self._used.get(key, 0) + 1
                    self.wasted += self._used[key] > self._allowed.get(key, 0)
        self.inventory[raw] = self.inventory.get(raw, 0) + 1
        self.crafted += 1
        goal = raw == w.goal
        self._stuck = not goal and not feasible(w, self.stock, self.inventory)
        return ToolResult.success(CraftedView(raw, k, self._held(), goal, self._stuck))

    def _held(self) -> tuple[tuple[str, int], ...]:
        """The inventory in display order: raw materials in stock order, then crafted items by
        name; empty entries left out."""
        raws = [(n, self.inventory[n]) for n in self.stock if self.inventory.get(n, 0) > 0]
        made = sorted((n, c) for n, c in self.inventory.items() if c > 0 and n not in self.stock)
        return tuple(raws + made)

    def _next_attempt(self) -> None:
        self.stock = dict(self.workshop.stock)
        self.inventory = {}
        self._used = {}
        self.attempt += 1
        if self.on_restart is not None:
            self.on_restart()

    def _append(self, entry: LogEntry) -> None:
        self.log.append(entry)
        if self.on_step is not None:
            self.on_step(entry)


def _shown(raw: object) -> str:
    return raw if isinstance(raw, str) else repr(raw)
