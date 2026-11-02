"""Agent-facing result types for the warehouse. Architectures may import this module.

The envelope is the other problems' (`ok`, `error`, `data`); see specs/012
contracts/warehouse-tools.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_DIRECTION = "invalid_direction"
    SHELF = "shelf"
    EDGE = "edge"
    NO_PACKAGE = "no_package"
    ALREADY_CARRYING = "already_carrying"
    NOT_ON_DROP = "not_on_drop"
    NOT_CARRYING = "not_carrying"
    UNKNOWN_TOOL = "unknown_tool"
    EPISODE_OVER = "episode_over"


class EndReason(StrEnum):
    DELIVERED = "delivered"
    BUDGET = "budget"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class RobotView:
    cell: str
    corridors: tuple[str, ...]
    packages_seen: tuple[tuple[str, str], ...]  # (package, cell)
    carrying: str | None
    on_drop: bool
    delivered: int
    packages: int
    columns: int
    rows: int

    def to_dict(self) -> dict[str, object]:
        return {
            "cell": self.cell,
            "corridors": list(self.corridors),
            "packages_seen": [{"package": p, "cell": c} for p, c in self.packages_seen],
            "carrying": self.carrying,
            "on_drop": self.on_drop,
            "delivered": self.delivered,
            "packages": self.packages,
            "columns": self.columns,
            "rows": self.rows,
        }


@dataclass(frozen=True, slots=True)
class StartView:
    """The first robot's view plus the floor plan, given free at the start."""

    view: RobotView
    floor: tuple[str, ...]
    aisles: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {**self.view.to_dict(), "floor": list(self.floor), "aisles": list(self.aisles)}


@dataclass(frozen=True, slots=True)
class Picked:
    picked: str
    cell: str

    def to_dict(self) -> dict[str, object]:
        return {"picked": self.picked, "cell": self.cell}


@dataclass(frozen=True, slots=True)
class Dropped:
    delivered_package: str
    delivered: int
    packages: int

    def to_dict(self) -> dict[str, object]:
        return {
            "delivered_package": self.delivered_package,
            "delivered": self.delivered,
            "packages": self.packages,
        }


@dataclass(frozen=True, slots=True)
class ToolError:
    code: ErrorCode
    message: str

    def to_dict(self) -> dict[str, object]:
        return {"code": str(self.code), "message": self.message}


Data = RobotView | StartView | Picked | Dropped


@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    error: ToolError | None
    data: Data | None

    @classmethod
    def success(cls, data: Data) -> ToolResult:
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
