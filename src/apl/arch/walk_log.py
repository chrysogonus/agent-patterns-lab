"""A2's explicit memory on the rune floor: the floor and every walk (specs/010 research R12).

It reads the result JSON the model also sees, never the environment (Constitution II), and draws no
conclusion about the rule. `record` (A6 only) lists what happened each time a tile was stepped on.
Written by the agent at the experimenter's request.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

COLUMNS = "ABCDEFGHIJ"
STEP = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}

Cell = tuple[int, int]


def parse(name: str) -> Cell:
    return COLUMNS.index(name[0]), int(name[1:]) - 1


def cell_name(cell: Cell) -> str:
    return COLUMNS[cell[0]] + str(cell[1] + 1)


@dataclass
class WalkNote:
    steps: list[tuple[Cell, str]] = field(default_factory=list)  # (cell, color) in order
    ending: str = ""  # "trap at D3 (yellow)", "back on start", "goal"; "" while open
    trap: Cell | None = None

    def render(self) -> str:
        cells = ", ".join(f"{cell_name(c)} {color}" for c, color in self.steps)
        if not self.ending:
            return f"(current) {cells or 'none yet'}"
        return f"{cells or 'none'} → {self.ending}"


@dataclass
class WalkLog:
    columns: int
    rows: int
    start: Cell
    goal: Cell
    floor: list[list[str]]
    position: Cell
    walks: list[WalkNote] = field(default_factory=lambda: [WalkNote()])

    @classmethod
    def from_start(cls, start_json: str) -> "WalkLog":
        data = json.loads(start_json)["data"]
        return cls(
            int(data["columns"]),
            int(data["rows"]),
            parse(data["start"]),
            parse(data["goal"]),
            [list(row) for row in data["floor"]],
            parse(data["position"]),
        )

    def apply(self, name: str, args: Mapping[str, Any], result: Mapping[str, Any]) -> None:
        """Update from one call and its result; failed calls change nothing."""
        if not result.get("ok"):
            return
        data = result["data"]
        if name == "look":
            self.floor = [list(row) for row in data["floor"]]
            self.position = parse(data["position"])
            return
        if name != "move":
            return
        current = self.walks[-1]
        if "trap" in data:
            trap = parse(data["trap"])
            current.ending, current.trap = f"trap at {data['trap']} ({data['color']})", trap
            self.walks.append(WalkNote())
        elif data.get("goal"):
            current.ending = "goal"
        elif data["color"] == "start":
            current.ending = "back on start"
            self.walks.append(WalkNote())
        else:
            current.steps.append((parse(data["position"]), str(data["color"])))
        self.position = parse(data["position"])

    @property
    def known(self) -> int:
        """Distinct cells stepped on, traps included: A4's measure of progress."""
        cells = {c for w in self.walks for c, _ in w.steps}
        return len(cells | {w.trap for w in self.walks if w.trap is not None})

    def render(self) -> str:
        lines = [
            f"Floor: {self.columns} columns × {self.rows} rows. "
            f"Start {cell_name(self.start)}, goal {cell_name(self.goal)}.",
            *(f"Row {y}: {' '.join(row)}" for y, row in enumerate(self.floor, 1)),
            f"You are on {cell_name(self.position)}.",
            "Walks so far:",
            *(f"{i}. {w.render()}" for i, w in enumerate(self.walks, 1)),
        ]
        return "\n".join(lines)

    def record(self, cell: Cell) -> list[tuple[int, str]]:
        """Every (walk step, "safe" | "trap") for that cell, in the order they happened."""
        found = []
        for walk in self.walks:
            found += [(i, "safe") for i, (c, _) in enumerate(walk.steps, 1) if c == cell]
            if walk.trap == cell:
                found.append((len(walk.steps) + 1, "trap"))
        return found

    def neighbor(self, direction: str) -> Cell | None:
        """The cell one step from the agent's, or None off the floor."""
        dx, dy = STEP[direction]
        x, y = self.position[0] + dx, self.position[1] + dy
        return (x, y) if 0 <= x < self.columns and 0 <= y < self.rows else None

    def color(self, cell: Cell) -> str:
        return self.floor[cell[1]][cell[0]]
