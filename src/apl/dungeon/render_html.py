"""Self-contained HTML picture of a dungeon; with frames, an animated player (research R9)."""

import html
import importlib.resources
import json

from apl.dungeon.frames import Frame
from apl.dungeon.model import Dungeon, Edge, Layout, Pos

CELL = 64
MARGIN = 24
GAP = 24  # width of a door opening in a wall


def _door_id(edge: Edge) -> str:
    return f"door-{edge.a[0]}-{edge.a[1]}-{edge.b[0]}-{edge.b[1]}"


def _wall(layout: Layout, a: Pos, b: Pos | None, x1: int, y1: int, x2: int, y2: int) -> list[str]:
    """One wall segment between rooms a and b (b is None on the outer border)."""
    edge = Edge(a, b) if b is not None and layout.in_grid(b) else None
    if edge is None or edge not in layout.doors:
        return [f'<line class="wall" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>']
    # Leave an opening in the middle of the wall; a locked door fills it with its color.
    mx, my = (x1 + x2) // 2, (y1 + y2) // 2
    dx, dy = (GAP // 2, 0) if y1 == y2 else (0, GAP // 2)
    parts = [
        f'<line class="wall" x1="{x1}" y1="{y1}" x2="{mx - dx}" y2="{my - dy}"/>',
        f'<line class="wall" x1="{mx + dx}" y1="{my + dy}" x2="{x2}" y2="{y2}"/>',
    ]
    color = layout.locks.get(edge)
    if color is not None:
        parts.append(
            f'<line class="lock c-{color}" id="{_door_id(edge)}" data-color="{color}" '
            f'x1="{mx - dx}" y1="{my - dy}" x2="{mx + dx}" y2="{my + dy}">'
            f"<title>{color} door</title></line>"
        )
    return parts


def svg(layout: Layout, animated: bool) -> str:
    """The dungeon as inline SVG; the viewer draws this too (specs/003 research R6)."""
    n, size = layout.size, 2 * MARGIN + layout.size * CELL
    out = [
        f'<svg viewBox="0 0 {size} {size}" role="img" aria-label="Dungeon map">',
        f'<rect class="floor" x="{MARGIN}" y="{MARGIN}" width="{n * CELL}" height="{n * CELL}"/>',
    ]
    if animated:
        out.append(f'<rect id="fail" x="0" y="0" width="{CELL}" height="{CELL}"/>')
    for x, y in layout.rooms():
        left, top = MARGIN + x * CELL, MARGIN + y * CELL
        label = html.escape(layout.labels[(x, y)])
        out.append(f'<text class="label" x="{left + 6}" y="{top + 16}">{label}</text>')
        if (x, y) == layout.start:
            out.append(
                f'<text id="start" class="marker" x="{left + 8}" y="{top + CELL - 10}">S</text>'
            )
        if (x, y) == layout.exit:
            out.append(
                f'<rect id="exit" x="{left + 4}" y="{top + 4}" '
                f'width="{CELL - 8}" height="{CELL - 8}"><title>exit</title></rect>'
            )
            out.append(f'<text class="marker" x="{left + CELL - 20}" y="{top + 20}">E</text>')
        # Each room draws its north and west walls; the last row and column add south and east.
        out += _wall(layout, (x, y), (x, y - 1), left, top, left + CELL, top)
        out += _wall(layout, (x, y), (x - 1, y), left, top, left, top + CELL)
        if y == n - 1:
            out += _wall(layout, (x, y), None, left, top + CELL, left + CELL, top + CELL)
        if x == n - 1:
            out += _wall(layout, (x, y), None, left + CELL, top, left + CELL, top + CELL)
    for color, (x, y) in sorted(layout.keys.items()):
        cx, cy = MARGIN + x * CELL + CELL - 16, MARGIN + y * CELL + CELL - 16
        out.append(
            f'<circle class="key c-{color}" id="key-{color}" data-color="{color}" '
            f'cx="{cx}" cy="{cy}" r="7"><title>{color} key</title></circle>'
        )
    # Room overlays above the drawing and below the agent: the viewer's "agent's view" dims them.
    for x, y in layout.rooms():
        out.append(
            f'<rect class="room" id="room-{x}-{y}" x="{MARGIN + x * CELL}" '
            f'y="{MARGIN + y * CELL}" width="{CELL}" height="{CELL}"/>'
        )
    if animated:
        start_x, start_y = (MARGIN + c * CELL + CELL // 2 for c in layout.start)
        out.append('<polyline id="trail" points=""/>')
        out.append(f'<circle id="agent" cx="{start_x}" cy="{start_y}" r="11"/>')
    out.append("</svg>")
    return "\n".join(out)


def render_html(dungeon: Dungeon, frames: list[Frame] | None = None) -> str:
    """One offline HTML file: a still picture, or with frames an animation of the route."""
    template = (importlib.resources.files("apl.dungeon") / "assets" / "player.html").read_text(
        encoding="utf-8"
    )
    if dungeon.level is not None:
        title = f"{dungeon.level.name} seed {dungeon.seed}"
    else:
        title = "Hand-built dungeon"
    page = template.replace("{{TITLE}}", html.escape(title))
    page = page.replace("{{SVG}}", svg(dungeon.layout, animated=frames is not None))
    head, _, rest = page.partition("<!--PLAYER-->\n")
    player, _, tail = rest.partition("<!--/PLAYER-->\n")
    if frames is None:
        return head + tail
    data = {"cell": CELL, "margin": MARGIN, "frames": [f.to_dict() for f in frames]}
    # "</" inside the JSON would end the script element early.
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).replace("</", "<\\/")
    return head + player.replace("{{FRAMES}}", payload) + tail
