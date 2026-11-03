"""One episode on one pipe: steps, budget, answers, attempts, log. Runner side only.

Architectures get an `AgentTools` (apl.signal_trace.tools) wrapping an Episode, never the Episode.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from apl.signal_trace.model import Action, Pipe
from apl.signal_trace.results import (
    EndReason,
    ErrorCode,
    LayoutView,
    ProbeView,
    RunView,
    Submitted,
    ToolResult,
)
from apl.signal_trace.strategy import Answer, informative, suspects

MAX_ATTEMPTS = 3  # for a retrying architecture, as on the other problems (specs/007)


@dataclass(frozen=True, slots=True)
class LogEntry:
    index: int
    step: int | None  # None for uncounted episode_over calls
    action: Action
    result: ToolResult
    attempt: int = 1
    wasted: bool = False  # a probe whose answer was already implied (research R7)
    scout: int = 0  # one agent; the viewer reads it as on the other problems

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "step": self.step,
            **({"attempt": self.attempt} if self.attempt > 1 else {}),
            **({"wasted": True} if self.wasted else {}),
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
    submitted_segment: int | None
    broken_segment: int
    segments: int
    probes: int
    wasted_probes: int
    reference_is_optimal: bool
    attempts: int = 1  # the attempt the episode ended in (specs/007)

    @property
    def scouts(self) -> int:
        return 1 if self.log else 0

    @property
    def success(self) -> bool:
        return (
            self.end_reason == EndReason.SUBMITTED and self.submitted_segment == self.broken_segment
        )

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
            "submitted_segment": self.submitted_segment,
            "broken_segment": self.broken_segment,
            "segments": self.segments,
            "probes": self.probes,
            "wasted_probes": self.wasted_probes,
            "reference_is_optimal": self.reference_is_optimal,
            **({"attempts": self.attempts} if self.attempts > 1 else {}),
            "log": [e.to_dict() for e in self.log],
        }


def start_episode(pipe: Pipe) -> Episode:
    return Episode(pipe)


def _segment(raw: object, segments: int) -> int | None:
    # A JSON integer, or a string of digits (models sometimes quote numbers); research R8.
    if isinstance(raw, bool):
        return None
    # At most 6 digits: a longer string is no segment, and int() refuses very long ones.
    if isinstance(raw, str) and raw.isascii() and raw.isdigit() and len(raw) <= 6:
        raw = int(raw)
    if isinstance(raw, int) and 1 <= raw <= segments:
        return raw
    return None


class Episode:
    def __init__(self, pipe: Pipe) -> None:
        self.pipe = pipe
        self.steps = 0
        self.invalid_actions = 0
        self.answers: list[Answer] = []  # this attempt's
        self.probes = 0  # successful probes, every attempt
        self.wasted_probes = 0
        self.submitted: int | None = None
        self.end_reason: EndReason | None = None
        self.log: list[LogEntry] = []
        self.on_step: Callable[[LogEntry], None] | None = None  # an observer, e.g. the viewer
        self.attempt = 1
        self.max_attempts = 1  # MAX_ATTEMPTS for a retrying architecture (specs/007 R2)
        self.on_restart: Callable[[], None] | None = None  # an observer, e.g. the viewer

    def add_scout(self) -> int | None:
        """The signal trace has one agent (research R9)."""
        return None

    def restart(self) -> bool:
        """The pipe back in its start state for the next attempt; steps and log go on.

        Costs no step. Refused once the episode is over or the attempts are used up.
        """
        if self.end_reason is not None or self.attempt >= self.max_attempts:
            return False
        self.answers = []
        self.submitted = None
        self.attempt += 1
        if self.on_restart is not None:
            self.on_restart()
        return True

    def describe(self) -> LayoutView:
        """The layout, as the agent sees it. Free: does not count as a step."""
        runs = tuple(RunView(r.feeder, r.first, r.last) for r in self.pipe.runs)
        return LayoutView(self.pipe.segments, runs)

    def suspects(self) -> frozenset[int]:
        """The segments still consistent with this attempt's answers."""
        return suspects(self.pipe.feeder, self.answers)

    def look(self) -> ToolResult:
        return self._call(Action("look"), lambda: ToolResult.success(self.describe()))

    def probe(self, raw: object) -> ToolResult:
        return self._call(Action("probe", (_shown(raw),)), lambda: self._probe(raw))

    def submit(self, raw: object) -> ToolResult:
        return self._call(Action("submit", (_shown(raw),)), lambda: self._submit(raw))

    def unknown(self, name: str) -> ToolResult:
        """A call to a tool that does not exist. It still costs a step (Constitution III)."""
        message = f"There is no tool named {name!r}. The tools are look, probe and submit."
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
        p = self.pipe
        return Outcome(
            level=p.level.name if p.level else None,
            seed=p.seed,
            end_reason=self.end_reason,
            steps=self.steps,
            optimal_steps=p.reference_steps,
            budget=p.budget,
            invalid_actions=self.invalid_actions,
            log=tuple(self.log),
            submitted_segment=self.submitted,
            broken_segment=p.broken,
            segments=p.segments,
            probes=self.probes,
            wasted_probes=self.wasted_probes,
            reference_is_optimal=p.reference_is_optimal,
            attempts=self.attempt,
        )

    def _call(self, action: Action, handler: Callable[[], ToolResult]) -> ToolResult:
        if self.end_reason is not None:
            result = ToolResult.failure(ErrorCode.EPISODE_OVER, "The episode is over.")
            self._append(LogEntry(len(self.log), None, action, result, self.attempt))
            return result
        self.steps += 1
        attempt = self.attempt
        wasted_before = self.wasted_probes
        result = handler()
        if not result.ok:
            self.invalid_actions += 1
        retry = self.submitted is not None and self._retries_wrong_segment()
        # A submission on the last step counts before the budget.
        if self.submitted is not None and not retry:
            self.end_reason = EndReason.SUBMITTED
        elif self.steps >= self.pipe.budget:
            self.end_reason = EndReason.BUDGET
        if retry and self.end_reason is None:
            # A wrong segment ends a retrying architecture's attempt (specs/007 research R3).
            result = ToolResult.success(
                Submitted(self.submitted or 0, False, self.max_attempts - self.attempt)
            )
        wasted = self.wasted_probes > wasted_before
        self._append(LogEntry(len(self.log), self.steps, action, result, attempt, wasted))
        if retry and self.end_reason is None:
            self.restart()
        return result

    def _retries_wrong_segment(self) -> bool:
        return self.submitted != self.pipe.broken and self.attempt < self.max_attempts

    def _append(self, entry: LogEntry) -> None:
        self.log.append(entry)
        if self.on_step is not None:
            self.on_step(entry)

    def _bad(self, raw: object) -> ToolResult:
        return ToolResult.failure(
            ErrorCode.NO_SUCH_SEGMENT,
            f"{raw!r} is not a segment; segments are numbered 1 to {self.pipe.segments}.",
        )

    def _probe(self, raw: object) -> ToolResult:
        segment = _segment(raw, self.pipe.segments)
        if segment is None:
            return self._bad(raw)
        if not informative(self.pipe.feeder, self.suspects(), segment):
            self.wasted_probes += 1
        water = self.pipe.wet(segment)
        self.answers.append((segment, water))
        self.probes += 1
        return ToolResult.success(ProbeView(segment, water))

    def _submit(self, raw: object) -> ToolResult:
        segment = _segment(raw, self.pipe.segments)
        if segment is None:
            return self._bad(raw)
        self.submitted = segment
        return ToolResult.success(Submitted(segment))


def _shown(raw: object) -> str:
    return raw if isinstance(raw, str) else repr(raw)
