"""A2's explicit memory on the survey field: a map built only from tool results (specs/005 R10).

It reads the result JSON the model also sees, never the environment (Constitution II). The
scouts of A7–A9 use it on the field through `SharedMap`. Written by the agent at the
experimenter's request.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

COLUMNS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIRECTIONS = ("north", "east", "south", "west")
STEP = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}


def _pos(name: str) -> tuple[int, int]:
    return COLUMNS.index(name[0]), int(name[1:]) - 1


def _name(col: int, row: int) -> str:
    return f"{COLUMNS[col]}{row + 1}"


@dataclass
class CellNote:
    deposit: bool
    exits: tuple[str, ...]


@dataclass
class FieldMap:
    columns: int
    rows: int
    cells: dict[str, CellNote] = field(default_factory=dict)  # by name, in the order first seen
    current: str = ""

    @classmethod
    def from_start(cls, start_json: str) -> "FieldMap":
        data = json.loads(start_json)["data"]
        found = cls(data["columns"], data["rows"])
        found._see(data)
        return found

    def _see(self, view: Mapping[str, Any]) -> None:
        self.cells[view["cell"]] = CellNote(bool(view["deposit"]), tuple(view["exits"]))
        self.current = view["cell"]

    def apply(self, name: str, args: Mapping[str, Any], result: Mapping[str, Any]) -> None:
        """One tool call and its result. Failures and submissions reveal nothing new."""
        if result.get("ok") and isinstance(result.get("data"), dict) and "cell" in result["data"]:
            self._see(result["data"])

    def _neighbor(self, name: str, direction: str) -> str | None:
        col, row = _pos(name)
        dx, dy = STEP[direction]
        col, row = col + dx, row + dy
        inside = 0 <= col < self.columns and 0 <= row < self.rows
        return _name(col, row) if inside else None

    def walls(self) -> list[str]:
        """Each wall a seen cell reports, once, as "<cell> <direction>"; the edge is not a wall."""
        found, done = [], set()
        for name, note in self.cells.items():
            for direction in DIRECTIONS:
                other = self._neighbor(name, direction)
                if other is None or direction in note.exits:
                    continue
                pair = frozenset((name, other))
                if pair not in done:
                    done.add(pair)
                    found.append(f"{name} {direction}")
        return found

    def frontier(self) -> list[str]:
        """Unseen cells one open step from a seen one, row by row, west to east."""
        found = {
            other
            for name, note in self.cells.items()
            for direction in note.exits
            if (other := self._neighbor(name, direction)) is not None and other not in self.cells
        }
        return sorted(found, key=lambda n: (_pos(n)[1], _pos(n)[0]))

    def render(self, others: Mapping[int, str] | None = None, *, here: bool = True) -> str:
        """The map for whoever stands in `current`; `here=False` for an orchestrator (no `@`).

        `others` maps other scouts' numbers to their cells; they show as digits.
        """
        others = others or {}
        at = {cell: str(n) for n, cell in sorted(others.items(), reverse=True)}
        if here:
            at[self.current] = "@"
        last = COLUMNS[self.columns - 1]
        lines = ["Your map (built from your tool results so far):"]
        size = f"Field: {self.columns} columns (A–{last}) × {self.rows} rows (1–{self.rows})."
        lines.append(f"You are in: {self.current}. {size}" if here else size)
        lines.append("   " + " ".join(COLUMNS[: self.columns]))
        for row in range(self.rows):
            marks = []
            for col in range(self.columns):
                name = _name(col, row)
                note = self.cells.get(name)
                mark = "?" if note is None else ("o" if note.deposit else ".")
                marks.append(at.get(name, mark))
            lines.append(f"{row + 1:<2} " + " ".join(marks))
        legend = "@ you, " if here else ""
        legend += "digits other scouts, " if others else ""
        lines.append(legend + "o deposit, . seen without deposit, ? not seen yet.")
        deposits = sum(note.deposit for note in self.cells.values())
        total = self.columns * self.rows
        lines.append(f"Cells seen: {len(self.cells)} of {total}. Deposits seen: {deposits}.")
        lines.append("Walls seen: " + (", ".join(self.walls()) or "none") + ".")
        lines.append(
            "Unseen cells next to seen ones: " + (", ".join(self.frontier()) or "none") + "."
        )
        return "\n".join(lines)
