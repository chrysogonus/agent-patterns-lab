"""Agent-facing result types for the workshop. Architectures may import this module.

The envelope is the other problems' (`ok`, `error`, `data`); see specs/011
contracts/workshop-tools.md. No result shows a recipe the agent has not inspected.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

Counts = tuple[tuple[str, int], ...]  # (name, count) in display order


class ErrorCode(StrEnum):
    UNKNOWN_ITEM = "unknown_item"
    NOT_RAW = "not_raw"
    OUT_OF_STOCK = "out_of_stock"
    NO_SUCH_RECIPE = "no_such_recipe"
    MISSING_INPUTS = "missing_inputs"
    UNKNOWN_TOOL = "unknown_tool"
    EPISODE_OVER = "episode_over"


class EndReason(StrEnum):
    GOAL = "goal"
    STUCK = "stuck"
    BUDGET = "budget"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class StoreView:
    goal: str
    stock: Counts
    inventory: Counts

    def to_dict(self) -> dict[str, object]:
        return {"goal": self.goal, "stock": dict(self.stock), "inventory": dict(self.inventory)}


@dataclass(frozen=True, slots=True)
class RecipesView:
    item: str
    recipes: tuple[tuple[str, ...], ...]

    def to_dict(self) -> dict[str, object]:
        return {"item": self.item, "recipes": [list(r) for r in self.recipes]}


@dataclass(frozen=True, slots=True)
class RawView:
    item: str

    def to_dict(self) -> dict[str, object]:
        return {"item": self.item, "raw": True}


@dataclass(frozen=True, slots=True)
class GatheredView:
    gathered: str
    stock: int  # what is left of it
    inventory: Counts

    def to_dict(self) -> dict[str, object]:
        return {"gathered": self.gathered, "stock": self.stock, "inventory": dict(self.inventory)}


@dataclass(frozen=True, slots=True)
class CraftedView:
    crafted: str
    recipe: int
    inventory: Counts
    goal: bool = False
    stuck: bool = False  # the goal can no longer be made (research R5)
    attempts_left: int | None = None  # a retrying architecture's stuck craft (research R10)

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "crafted": self.crafted,
            "recipe": self.recipe,
            "inventory": dict(self.inventory),
        }
        if self.goal:
            out["goal"] = True
        if self.stuck:
            out["stuck"] = True
        if self.attempts_left is not None:
            out["attempts_left"] = self.attempts_left
        return out


Data = StoreView | RecipesView | RawView | GatheredView | CraftedView


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
