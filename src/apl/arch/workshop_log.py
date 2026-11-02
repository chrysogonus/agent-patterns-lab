"""The explicit memory of A2–A5 on the workshop: the goal, stock, inventory and recipes seen
(specs/011 research R12).

It reads the result JSON the model also sees, never the environment (Constitution II), and draws no
conclusion: no plan and no warning about scarce materials. `options` (A6 only) lists the actions
that can be taken now. Written by the agent at the experimenter's request.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

Call = tuple[str, dict[str, object]]
RAW = ()  # the recipes of an item inspected as a raw material


@dataclass
class WorkshopLog:
    goal: str
    stock: dict[str, int]
    inventory: dict[str, int]
    recipes: dict[str, tuple[tuple[str, ...], ...]] = field(default_factory=dict)  # inspected
    progress: int = 0  # new inspections plus successful gathers and crafts

    @classmethod
    def from_start(cls, start_json: str) -> "WorkshopLog":
        data = json.loads(start_json)["data"]
        return cls(str(data["goal"]), dict(data["stock"]), dict(data["inventory"]))

    def apply(self, name: str, args: Mapping[str, Any], result: Mapping[str, Any]) -> None:
        """Update from one call and its result; failed calls change nothing."""
        if not result.get("ok"):
            return
        data = result["data"]
        if name == "look":
            self.stock, self.inventory = dict(data["stock"]), dict(data["inventory"])
        elif name == "inspect":
            found = data.get("recipes")
            item = str(data["item"])
            self.progress += item not in self.recipes
            self.recipes[item] = RAW if data.get("raw") else tuple(map(tuple, found))
        elif name == "gather":
            self.stock[str(data["gathered"])] = int(data["stock"])
            self.inventory = dict(data["inventory"])
            self.progress += 1
        elif name == "craft" and "attempts_left" not in data:
            self.inventory = dict(data["inventory"])
            self.progress += 1

    @property
    def known(self) -> int:
        """Items inspected: A4's measure of progress."""
        return len(self.recipes)

    def render(self) -> str:
        stock = ", ".join(f"{name} {n}" for name, n in self.stock.items())
        held = ", ".join(f"{name} {n}" for name, n in self.inventory.items()) or "empty"
        lines = [f"Goal: {self.goal}.", f"Stock: {stock}.", f"Inventory: {held}."]
        if not self.recipes:
            lines.append("Recipes seen: none.")
            return "\n".join(lines)
        lines.append(f"Recipes seen ({len(self.recipes)}):")
        for item, recipes in self.recipes.items():
            if recipes == RAW:
                lines.append(f"- {item}: raw material")
            elif len(recipes) == 1:
                lines.append(f"- {item}: {', '.join(recipes[0])}")
            else:
                said = "; ".join(f"recipe {k}: {', '.join(r)}" for k, r in enumerate(recipes, 1))
                lines.append(f"- {item}: {said}")
        return "\n".join(lines)

    def options(self) -> list[tuple[str, Call]]:
        """A6's options: every action that can be taken now (contracts/architectures.md)."""
        found: list[tuple[str, Call]] = []
        named: list[str] = [self.goal]
        for recipes in self.recipes.values():
            for recipe in recipes:
                named += [n for n in recipe if n not in named]
        for item in named:
            if item not in self.stock and item not in self.recipes:
                found.append((f"inspect {item}", ("inspect", {"item": item})))
        for raw, n in self.stock.items():
            if n > 0:
                found.append((f"gather {raw} ({n} left)", ("gather", {"item": raw})))
        for item, recipes in self.recipes.items():
            for k, recipe in enumerate(recipes, 1):
                if self._holds(recipe):
                    text = f"craft {item} with recipe {k} (uses {', '.join(recipe)})"
                    found.append((text, ("craft", {"item": item, "recipe": k})))
        return found

    def _holds(self, recipe: tuple[str, ...]) -> bool:
        need: dict[str, int] = {}
        for name in recipe:
            need[name] = need.get(name, 0) + 1
        return all(self.inventory.get(n, 0) >= c for n, c in need.items())
