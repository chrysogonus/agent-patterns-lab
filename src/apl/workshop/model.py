"""The workshop's data types (specs/011 data-model.md). Runner side only."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

Recipe = tuple[str, ...]  # input names, one unit each

CRAFTABLE_NAMES = (
    "lantern", "frame", "lens", "oil", "iron bar", "glass", "wick", "handle", "hinge", "chain",
    "bracket", "plate", "rod", "spring", "gear", "valve", "pipe", "ring", "clasp", "shade",
)  # fmt: skip
RAW_NAMES = (
    "coal", "iron ore", "sand", "wood", "seeds", "clay", "copper ore", "flax", "resin", "stone",
    "tin", "wax", "lime", "salt",
)  # fmt: skip


@dataclass(frozen=True, slots=True)
class WorkshopLevel:
    name: str
    craftables: int  # craftable items in the tree under the goal
    depth: int  # levels of craftables, the goal's included
    conflicts: int  # scarce materials with a tempting first recipe (research R4)


LEVELS: dict[str, WorkshopLevel] = {
    "W1": WorkshopLevel("W1", 3, 2, 0),
    "W2": WorkshopLevel("W2", 5, 3, 1),
    "W3": WorkshopLevel("W3", 8, 4, 2),
    "W4": WorkshopLevel("W4", 12, 5, 3),
}


@dataclass(frozen=True, slots=True)
class Workshop:
    level: WorkshopLevel | None  # None for a hand-built workshop
    seed: int | None
    goal: str
    recipes: Mapping[str, tuple[Recipe, ...]]  # every craftable's recipes, in their fixed order
    stock: Mapping[str, int]  # every raw material's starting count, by name
    scarce: frozenset[str]  # raw materials with a conflict (stock 1)
    reference_choice: Mapping[str, int]  # the reference plan's recipe (1-based) where there are two
    reference: int  # steps of the reference plan (research R6)

    @property
    def reference_steps(self) -> int:
        return self.reference

    @property
    def budget(self) -> int:
        return 3 * self.reference  # spec FR-009

    @property
    def reference_is_optimal(self) -> bool:
        return True

    def raw(self, name: object) -> bool:
        return isinstance(name, str) and name in self.stock

    def craftable(self, name: object) -> bool:
        return isinstance(name, str) and name in self.recipes


@dataclass(frozen=True, slots=True)
class Action:
    tool: str  # look, inspect, gather, craft, or unknown
    args: tuple[str, ...] = ()

    def __str__(self) -> str:
        return " ".join((self.tool, *self.args))

    def to_dict(self) -> dict[str, object]:
        return {"tool": self.tool, "args": list(self.args)}
