"""A2's explicit memory in the warehouse: a floor map built only from tool results (specs/012 R12).

It reads the result JSON the model also sees, never the environment (Constitution II), and draws no
conclusion from it. The scouts of A7–A9 use it through `SharedMap`, which keeps each robot's cell
and carried package. Written by the agent at the experimenter's request.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

COLUMNS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
WEST, EAST = "west corridor", "east corridor"


def _pos(name: str) -> tuple[int, int]:
    return COLUMNS.index(name[0]), int(name[1:]) - 1


def _name(col: int, row: int) -> str:
    return f"{COLUMNS[col]}{row + 1}"


@dataclass
class FloorMap:
    columns: int
    rows: int
    floor: list[str]  # the free floor plan: "#", ".", "S", "D"
    aisles: list[str]
    total: int  # packages in the warehouse
    current: str = ""
    carrying: str | None = None
    delivered: int = 0
    seen: list[str] = field(default_factory=list)  # corridor names, in the order first seen
    packages: dict[str, str] = field(default_factory=dict)  # waiting, as last seen: name -> cell

    @classmethod
    def from_start(cls, start_json: str) -> "FloorMap":
        data = json.loads(start_json)["data"]
        found = cls(
            data["columns"], data["rows"], list(data["floor"]), list(data["aisles"]),
            data["packages"],
        )  # fmt: skip
        found._view(data)
        return found

    def _cells(self, corridor: str) -> set[str]:
        if corridor == WEST:
            return {_name(0, y) for y in range(self.rows)}
        if corridor == EAST:
            return {_name(self.columns - 1, y) for y in range(self.rows)}
        row = 2 * (int(corridor.removeprefix("aisle ")) - 1)
        return {_name(x, row) for x in range(self.columns)}

    def _view(self, view: Mapping[str, Any]) -> None:
        self.current, self.carrying = view["cell"], view["carrying"]
        self.delivered = view["delivered"]
        for corridor in view["corridors"]:
            if corridor not in self.seen:
                self.seen.append(corridor)
            cells = self._cells(corridor)
            self.packages = {n: c for n, c in self.packages.items() if c not in cells}
        for seen in view["packages_seen"]:
            self.packages[seen["package"]] = seen["cell"]

    def apply(self, name: str, args: Mapping[str, Any], result: Mapping[str, Any]) -> None:
        """One tool call and its result. Failed calls reveal nothing new."""
        data = result.get("data")
        if not result.get("ok") or not isinstance(data, dict):
            return
        if "corridors" in data:
            self._view(data)
        elif "picked" in data:
            self.carrying = data["picked"]
            self.packages.pop(data["picked"], None)
        elif "delivered_package" in data:
            self.carrying, self.delivered = None, data["delivered"]

    def render(self, others: Mapping[int, str] | None = None, *, here: bool = True) -> str:
        """The map for whoever stands in `current`; `here=False` for an orchestrator (no `@`).

        `others` maps other robots' numbers to their cells; they show as digits.
        """
        others = others or {}
        at = {cell: str(n) for n, cell in sorted(others.items(), reverse=True)}
        if here:
            at[self.current] = "@"
        waiting = {cell for cell in self.packages.values()}
        seen = set().union(*(self._cells(c) for c in self.seen)) if self.seen else set()
        lines = ["Your map (built from your tool results so far):"]
        delivered = f"Delivered: {self.delivered} of {self.total} packages."
        if here:
            corridors = ", ".join(c for c in self.seen if self.current in self._cells(c))
            carried = self.carrying or "nothing"
            lines.append(
                f"You are in: {self.current} ({corridors}). You carry: {carried}. {delivered}"
            )
        else:
            lines.append(delivered)
        lines.append("   " + " ".join(COLUMNS[: self.columns]))
        for row in range(self.rows):
            marks = []
            for col in range(self.columns):
                name, plan = _name(col, row), self.floor[row][col]
                if name in at:
                    marks.append(at[name])
                elif name in waiting:
                    marks.append("P")
                elif plan in "#SD":
                    marks.append(plan)
                else:
                    marks.append("." if name in seen else "?")
            lines.append(f"{row + 1:<2} " + " ".join(marks))
        legend = "@ you, " if here else ""
        legend += "digits other robots, " if others else ""
        lines.append(legend + "# shelf, P package, . seen, ? not seen yet, S dock, D drop zone.")
        unseen = [c for c in [*self.aisles, WEST, EAST] if c not in self.seen]
        lines.append(
            f"Corridors seen: {', '.join(self.seen)}. Not seen yet: {', '.join(unseen) or 'none'}."
        )
        listed = [f"{n} at {c}" for n, c in sorted(self.packages.items(), key=lambda p: p[0])]
        lines.append("Packages seen: " + (", ".join(listed) or "none") + ".")
        return "\n".join(lines)
