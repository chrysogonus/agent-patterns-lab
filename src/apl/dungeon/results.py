"""Agent-facing result types. Architectures may import this module (see contracts/tools.md)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from apl.dungeon.model import Direction


class ErrorCode(StrEnum):
    INVALID_DIRECTION = "invalid_direction"
    NO_DOOR = "no_door"
    LOCKED = "locked"
    NO_SUCH_ITEM = "no_such_item"
    NOT_IN_INVENTORY = "not_in_inventory"
    WRONG_KEY = "wrong_key"
    NOT_LOCKED = "not_locked"
    EPISODE_OVER = "episode_over"
    UNKNOWN_TOOL = "unknown_tool"


class EndReason(StrEnum):
    EXIT = "exit"
    BUDGET = "budget"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class ExitView:
    direction: Direction
    lock: str | None  # the color while locked; None once open or if never locked

    def to_dict(self) -> dict[str, object]:
        return {"direction": str(self.direction), "lock": self.lock}


@dataclass(frozen=True, slots=True)
class RoomView:
    label: str
    exits: tuple[ExitView, ...]
    items: tuple[str, ...]
    inventory: tuple[str, ...]
    is_exit: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "exits": [e.to_dict() for e in self.exits],
            "items": list(self.items),
            "inventory": list(self.inventory),
            "is_exit": self.is_exit,
        }


@dataclass(frozen=True, slots=True)
class InventoryView:
    inventory: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {"inventory": list(self.inventory)}


@dataclass(frozen=True, slots=True)
class DoorOpened:
    direction: Direction
    color: str

    def to_dict(self) -> dict[str, object]:
        return {"direction": str(self.direction), "color": self.color}


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
    data: RoomView | InventoryView | DoorOpened | None

    @classmethod
    def success(cls, data: RoomView | InventoryView | DoorOpened) -> ToolResult:
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
