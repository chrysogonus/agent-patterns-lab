"""A2's explicit memory: a map built only from tool results (specs/003 research R13, R14).

It reads the result JSON the model also sees, never the environment (Constitution II). A3 and A6
can reuse it.
"""

import json
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

DIRECTIONS = ("north", "east", "south", "west")
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}


@dataclass
class RoomNote:
    exits: dict[str, str | None]  # direction -> lock color as last seen (None: no lock)
    leads_to: dict[str, str] = field(default_factory=dict)  # direction -> room label, once walked
    items: list[str] = field(default_factory=list)


@dataclass
class DungeonMap:
    rooms: dict[str, RoomNote]  # by label, in the order first seen
    current: str
    inventory: tuple[str, ...] = ()
    opened: list[tuple[str, str, str]] = field(default_factory=list)  # (room, direction, color)

    @classmethod
    def from_start(cls, start_json: str) -> "DungeonMap":
        data = json.loads(start_json)["data"]
        found = cls({}, data["label"])
        found._see(data)
        return found

    def _see(self, room: Mapping[str, Any]) -> None:
        label = room["label"]
        note = self.rooms.setdefault(label, RoomNote({}))
        note.exits = {e["direction"]: e["lock"] for e in room["exits"]}
        note.items = list(room["items"])
        self.inventory = tuple(room["inventory"])
        self.current = label

    def apply(self, name: str, args: Mapping[str, Any], result: Mapping[str, Any]) -> None:
        """One tool call and its result. Failures reveal nothing the room view did not show."""
        if not result.get("ok"):
            return
        data = result["data"]
        here = self.rooms[self.current]
        if name == "move":
            direction, before = args["direction"], self.current
            self._see(data)
            self.rooms[before].leads_to[direction] = data["label"]
            # A door between two rooms works both ways (the base prompt's rules).
            self.rooms[data["label"]].leads_to[OPPOSITE[direction]] = before
        elif name == "look":
            self._see(data)
        elif name == "take":
            taken = set(data["inventory"]) - set(self.inventory)
            self.inventory = tuple(data["inventory"])
            here.items = [i for i in here.items if i not in taken]
        elif name == "use":
            direction, color = data["direction"], data["color"]
            here.exits[direction] = None
            self.opened.append((self.current, direction, color))
            if (other := here.leads_to.get(direction)) is not None:
                self.rooms[other].exits[OPPOSITE[direction]] = None

    def unexplored(self, label: str) -> list[str]:
        room = self.rooms[label]
        return [d for d in DIRECTIONS if d in room.exits and d not in room.leads_to]

    def paths(self) -> dict[str, list[str]]:
        """The shortest moves from here to each room, over doors already walked."""
        paths = {self.current: list[str]()}
        queue = deque([self.current])
        while queue:
            label = queue.popleft()
            for d, other in self.rooms[label].leads_to.items():
                if other not in paths:
                    paths[other] = [*paths[label], d]
                    queue.append(other)
        return paths

    def routes(self) -> list[tuple[str, str, list[str]]]:
        """(room, unexplored exit, moves from here through it), nearest first, over walked doors."""
        paths = self.paths()
        found = [(r, d, [*paths[r], d]) for r in self.rooms for d in self.unexplored(r)]
        return sorted(found, key=lambda route: len(route[2]))

    def render(self, routes: bool = False) -> str:
        inventory = ", ".join(self.inventory) or "nothing"
        lines = [
            "Your map (built from your tool results so far):",
            f"You are in: {self.current}. Inventory: {inventory}.",
            "Rooms seen:",
        ]
        frontier = []
        for label, room in self.rooms.items():
            parts = []
            for d in DIRECTIONS:
                if d not in room.exits:
                    continue
                lock = room.exits[d]
                if d in room.leads_to:
                    parts.append(f"{d} -> {room.leads_to[d]}")
                else:
                    parts.append(f"{d}: unexplored" + (f", locked ({lock})" if lock else ""))
                    frontier.append(f"{label} {d}" + (f" (locked, {lock})" if lock else ""))
            if room.items:
                parts.append("items: " + ", ".join(room.items))
            here = " (you are here)" if label == self.current else ""
            lines.append(f"- {label}{here}: " + "; ".join(parts))
        if self.opened:
            lines.append(
                "Doors you opened: " + "; ".join(f"{r} {d} ({c})" for r, d, c in self.opened) + "."
            )
        if routes and frontier:
            lines.append("Routes to unexplored exits (through doors you have walked):")
            for target, d, moves in self.routes():
                lock = self.rooms[target].exits[d]
                locked = f", locked ({lock})" if lock else ""
                count = f"{len(moves)} move" + ("s" if len(moves) > 1 else "")
                lines.append(f"- {target} {d}{locked} ({count}): " + ", ".join(moves))
        else:
            lines.append("Unexplored exits: " + ("; ".join(frontier) if frontier else "none") + ".")
        return "\n".join(lines)
