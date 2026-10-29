"""ASCII map of a dungeon, with an optional route overlay and step table (contracts/cli.md)."""

from apl.dungeon.frames import Frame
from apl.dungeon.model import Dungeon, Edge, Layout, Pos


def _markers(layout: Layout, room: Pos, visited: set[Pos]) -> str:
    marks = "S" if room == layout.start else ""
    marks += "E" if room == layout.exit else ""
    marks += "".join(c[0] for c, p in sorted(layout.keys.items()) if p == room)
    return marks + ("*" if room in visited else "")


def _wall(layout: Layout, a: Pos, b: Pos, wall: str, gap: str) -> str:
    edge = Edge(a, b)
    if edge not in layout.doors:
        return wall
    color = layout.locks.get(edge)
    return color[0].upper() if color else gap


def _grid(layout: Layout, visited: set[Pos]) -> str:
    n = layout.size
    cells = {r: f" {layout.labels[r]}{_markers(layout, r, visited)}" for r in layout.rooms()}
    width = max(len(c) for c in cells.values()) + 1
    left = (width - 2) // 2

    def horizontal(y: int) -> str:
        parts = []
        for x in range(n):
            if y in (0, n):
                parts.append("-" * width)
            else:
                door = _wall(layout, (x, y - 1), (x, y), "-", "  ")
                parts.append("-" * left + door + "-" * (width - left - len(door)))
        return "+" + "+".join(parts) + "+"

    lines = []
    for y in range(n):
        lines.append(horizontal(y))
        row = "|"
        for x in range(n):
            row += cells[(x, y)].ljust(width)
            row += "|" if x == n - 1 else _wall(layout, (x, y), (x + 1, y), "|", " ")
        lines.append(row)
    lines.append(horizontal(n))
    return "\n".join(lines)


def _result(frame: Frame) -> str:
    if frame.action is None:
        return ""
    if not frame.ok:
        return str(frame.error_code)
    if frame.action.tool == "take":
        return f"ok, took {frame.action.args[0]}"
    if frame.action.tool == "use":
        return f"ok, opened {frame.action.args[0].removesuffix(' key')}"
    return "ok"


def _table(layout: Layout, frames: list[Frame]) -> str:
    labels = layout.labels
    lines = ["step  room  action                    result"]
    for f in frames:
        action = str(f.action) if f.action else "(start)"
        lines.append(f"{f.step:>4}  {labels[f.position]:<4}  {action:<24}  {_result(f)}".rstrip())
    visits: dict[Pos, list[int]] = {}
    for prev, f in zip([None, *frames], frames, strict=False):
        if prev is None or f.position != prev.position:
            visits.setdefault(f.position, []).append(f.step)
    numbers = (f"{labels[r]} {','.join(map(str, steps))}" for r, steps in visits.items())
    lines.append("visits: " + " | ".join(numbers))
    last = frames[-1]
    ended = last.end_reason or "not ended"
    lines.append(f"end: {labels[last.position]} at step {last.step} ({ended})")
    return "\n".join(lines)


def render_text(dungeon: Dungeon, frames: list[Frame] | None = None) -> str:
    """The map; with frames, rooms on the route get '*' and a step table follows."""
    layout = dungeon.layout
    visited = {f.position for f in frames} if frames else set()
    text = _grid(layout, visited)
    return f"{text}\n\n{_table(layout, frames)}\n" if frames else f"{text}\n"
