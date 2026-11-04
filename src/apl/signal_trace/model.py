"""The signal trace's data types (specs/009 data-model.md). Runner side only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SignalLevel:
    name: str
    segments: int
    ends: int  # pipe ends: segments that feed none
    min_run: int  # the shortest run allowed


LEVELS: dict[str, SignalLevel] = {
    "T1": SignalLevel("T1", segments=16, ends=1, min_run=16),
    "T2": SignalLevel("T2", segments=64, ends=1, min_run=64),
    "T3": SignalLevel("T3", segments=64, ends=4, min_run=4),
    "T4": SignalLevel("T4", segments=256, ends=8, min_run=4),
}


@dataclass(frozen=True, slots=True)
class Run:
    """A straight piece of pipe: `feeder` (0 for S) feeds `first`, each segment the next."""

    feeder: int
    first: int
    last: int


@dataclass(frozen=True, slots=True)
class Pipe:
    level: SignalLevel | None  # None for a hand-built pipe
    seed: int | None
    feeder: tuple[int, ...]  # feeder[k - 1] feeds segment k; 0 is S; always below k
    runs: tuple[Run, ...]  # in order of `first`
    broken: int
    reference_probes: int  # the worst case of the reference strategy (research R5)
    reference_is_optimal: bool

    @property
    def segments(self) -> int:
        return len(self.feeder)

    @property
    def reference_steps(self) -> int:
        return self.reference_probes + 1  # the probes, then the submission

    @property
    def budget(self) -> int:
        # The larger of 3× the reference and a full scan: N − 1 probes and the submission.
        return max(3 * self.reference_steps, self.segments)

    def upstream(self, segment: int) -> frozenset[int]:
        """The segment and every segment between it and S."""
        path = set()
        while segment:
            path.add(segment)
            segment = self.feeder[segment - 1]
        return frozenset(path)

    def wet(self, segment: int) -> bool:
        return self.broken not in self.upstream(segment)


@dataclass(frozen=True, slots=True)
class Action:
    tool: str  # look, probe, submit, or unknown
    args: tuple[str, ...] = ()

    def __str__(self) -> str:
        return " ".join((self.tool, *self.args))

    def to_dict(self) -> dict[str, object]:
        return {"tool": self.tool, "args": list(self.args)}
