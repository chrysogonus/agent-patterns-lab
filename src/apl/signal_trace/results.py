"""Agent-facing result types for the signal trace. Architectures may import this module.

The envelope is the other problems' (`ok`, `error`, `data`); see specs/009
contracts/signal-tools.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    NO_SUCH_SEGMENT = "no_such_segment"
    UNKNOWN_TOOL = "unknown_tool"
    EPISODE_OVER = "episode_over"


class EndReason(StrEnum):
    SUBMITTED = "submitted"
    BUDGET = "budget"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class RunView:
    feeder: int  # 0 is S
    first: int
    last: int

    def to_dict(self) -> dict[str, object]:
        return {
            "from": "S" if self.feeder == 0 else self.feeder,
            "first": self.first,
            "last": self.last,
        }


@dataclass(frozen=True, slots=True)
class LayoutView:
    segments: int
    runs: tuple[RunView, ...]

    def to_dict(self) -> dict[str, object]:
        return {"segments": self.segments, "runs": [r.to_dict() for r in self.runs]}


@dataclass(frozen=True, slots=True)
class ProbeView:
    segment: int
    water: bool

    def to_dict(self) -> dict[str, object]:
        return {"segment": self.segment, "water": self.water}


@dataclass(frozen=True, slots=True)
class Submitted:
    submitted: int
    # Only for a retrying architecture's wrong submission with attempts left (specs/007 R3): it
    # says the segment was wrong, never which one is broken.
    correct: bool | None = None
    attempts_left: int | None = None

    def to_dict(self) -> dict[str, object]:
        if self.correct is None:
            return {"submitted": self.submitted}
        return {
            "submitted": self.submitted,
            "correct": self.correct,
            "attempts_left": self.attempts_left,
        }


@dataclass(frozen=True, slots=True)
class ToolError:
    code: ErrorCode
    message: str

    def to_dict(self) -> dict[str, object]:
        return {"code": str(self.code), "message": self.message}


@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    error: ToolError | None
    data: LayoutView | ProbeView | Submitted | None

    @classmethod
    def success(cls, data: LayoutView | ProbeView | Submitted) -> ToolResult:
        return cls(True, None, data)

    @classmethod
    def failure(cls, code: ErrorCode, message: str) -> ToolResult:
        return cls(False, ToolError(code, message), None)

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "error": self.error.to_dict() if self.error else None,
            "data": self.data.to_dict() if self.data else None,
        }
