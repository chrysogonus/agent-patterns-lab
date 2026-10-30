"""Text map, route overlay, and HTML picture (SC-010, SC-011, FR-024 to FR-028)."""

import importlib.resources
import json
import re

import pytest

from apl.dungeon import DEV_SEEDS, LEVELS, generate
from apl.dungeon.frames import build_frames
from apl.dungeon.model import Action, Dungeon, Edge, Layout
from apl.dungeon.render_html import CELL, GAP, MARGIN, render_html, svg
from apl.dungeon.render_text import render_text
from tests.dungeon.reference import chained_keys

MARKERS = "SE*rbgy"


def _cell_markers(text: str, label: str) -> str:
    match = re.search(rf"{label}([{MARKERS}]*)", text)
    assert match, f"label {label} missing"
    return match.group(1)


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_text_map_shows_everything(level: str) -> None:
    for seed in DEV_SEEDS:
        dungeon = generate(level, seed)
        layout = dungeon.layout
        text = render_text(dungeon)
        grid = text.split("\n\n")[0]
        assert "S" in _cell_markers(grid, layout.labels[layout.start])
        assert "E" in _cell_markers(grid, layout.labels[layout.exit])
        for color, room in layout.keys.items():
            assert color[0] in _cell_markers(grid, layout.labels[room])
        lock_letters = sorted(c for c in grid if c in "RBGY")
        assert lock_letters == sorted(c[0].upper() for c in layout.locks.values())
        assert grid.count("S") == 1 and grid.count("E") == 1
        assert "*" not in grid
        assert render_text(dungeon) == text


def _text_doors(grid: str, layout: Layout) -> tuple[set[Edge], dict[Edge, str]]:
    """Rebuild open doors and lock letters from the text map; also checks every label."""
    n, lines = layout.size, grid.split("\n")
    width = len(lines[0].split("+")[1])
    doors: set[Edge] = set()
    locks: dict[Edge, str] = {}

    def record(edge: Edge, mark: str) -> None:
        letters = mark.strip(" -|")  # a lock letter, if any
        if letters:
            locks[edge] = letters
        if letters or " " in mark:  # a gap is an open door
            doors.add(edge)

    for y in range(n):
        row = lines[2 * y + 1]
        for x in range(n):
            start = 1 + x * (width + 1)
            assert row[start + 1 :].startswith(layout.labels[(x, y)]), (x, y)
            if x < n - 1:
                record(Edge((x, y), (x + 1, y)), row[start + width])
        if y > 0:
            for x, segment in enumerate(lines[2 * y].split("+")[1:-1]):
                record(Edge((x, y - 1), (x, y)), segment)
    return doors, locks


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_text_map_doors_round_trip(level: str) -> None:
    for seed in DEV_SEEDS:
        dungeon = generate(level, seed)
        layout = dungeon.layout
        doors, locks = _text_doors(render_text(dungeon).split("\n\n")[0], layout)
        assert doors == set(layout.doors)
        assert locks == {e: c[0].upper() for e, c in layout.locks.items()}


def _segment(edge: Edge) -> tuple[int, int, int, int]:
    """The wall segment between two neighboring rooms, in SVG coordinates."""
    (ax, ay), (bx, by) = edge.a, edge.b
    if ay == by:  # side by side: a vertical wall
        x = MARGIN + bx * CELL
        return (x, MARGIN + ay * CELL, x, MARGIN + ay * CELL + CELL)
    y = MARGIN + by * CELL
    return (MARGIN + ax * CELL, y, MARGIN + ax * CELL + CELL, y)


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_picture_walls_round_trip(level: str) -> None:
    line = re.compile(r'<line class="wall" x1="(\d+)" y1="(\d+)" x2="(\d+)" y2="(\d+)"/>')
    for seed in DEV_SEEDS:
        dungeon = generate(level, seed)
        layout, page = dungeon.layout, render_html(dungeon)
        n, end = layout.size, MARGIN + layout.size * CELL
        walls = [tuple(int(v) for v in m) for m in line.findall(page)]
        full = {w for w in walls if abs(w[2] - w[0]) + abs(w[3] - w[1]) == CELL}
        pieces = [w for w in walls if abs(w[2] - w[0]) + abs(w[3] - w[1]) == (CELL - GAP) // 2]
        inner = {Edge((x, y), (x + 1, y)) for y in range(n) for x in range(n - 1)}
        inner |= {Edge((x, y), (x, y + 1)) for y in range(n - 1) for x in range(n)}
        border = {(MARGIN + i * CELL, MARGIN, MARGIN + i * CELL + CELL, MARGIN) for i in range(n)}
        border |= {(MARGIN + i * CELL, end, MARGIN + i * CELL + CELL, end) for i in range(n)}
        border |= {(MARGIN, MARGIN + i * CELL, MARGIN, MARGIN + i * CELL + CELL) for i in range(n)}
        border |= {(end, MARGIN + i * CELL, end, MARGIN + i * CELL + CELL) for i in range(n)}
        assert full == {_segment(e) for e in inner - layout.doors} | border
        assert len(walls) == len(full) + len(pieces) and len(pieces) == 2 * len(layout.doors)
        lock_ids = set(re.findall(r'class="lock c-\w+" id="door-(\d+)-(\d+)-(\d+)-(\d+)"', page))
        assert {tuple(int(v) for v in i) for i in lock_ids} == {(*e.a, *e.b) for e in layout.locks}


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_overlay_marks_the_route_and_lists_steps(level: str) -> None:
    for seed in DEV_SEEDS:
        dungeon = generate(level, seed)
        frames = build_frames(dungeon, dungeon.solution.actions)
        text = render_text(dungeon, frames)
        labels = dungeon.layout.labels
        for frame in frames:
            assert "*" in _cell_markers(text.split("\n\n")[0], labels[frame.position])
        for color in dungeon.layout.keys:
            assert f"took {color} key" in text and f"opened {color}" in text
        assert text.rstrip().endswith("(exit)")
        assert render_text(dungeon, frames) == text


def test_overlay_shows_revisits_failures_and_where_it_ended() -> None:
    dungeon = Dungeon.from_layout(chained_keys())
    actions = [
        Action("move", ("south",)),
        Action("move", ("east",)),  # no door
        Action("move", ("north",)),
        Action("move", ("south",)),
    ]
    text = render_text(dungeon, build_frames(dungeon, actions))
    labels = dungeon.layout.labels
    assert "no_door" in text
    assert f"{labels[(0, 0)]} 0,3" in text
    assert f"{labels[(0, 1)]} 1,4" in text
    assert f"end: {labels[(0, 1)]} at step 4 (not ended)" in text


# --- HTML picture and animation (Story 5) ---

EXTERNAL = re.compile(r"https?:|['\"(]//|\bsrc=|\bhref=|url\(", re.IGNORECASE)


def _frames_json(page: str) -> dict[str, object]:
    match = re.search(r'<script type="application/json" id="apl-frames">(.*?)</script>', page, re.S)
    assert match
    data = json.loads(match.group(1))
    assert isinstance(data, dict)
    return data


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_picture_shows_everything(level: str) -> None:
    for seed in DEV_SEEDS:
        dungeon = generate(level, seed)
        layout = dungeon.layout
        page = render_html(dungeon)
        for label in layout.labels.values():
            assert f">{label}</text>" in page
        assert 'id="start"' in page and 'id="exit"' in page
        for edge, color in layout.locks.items():
            assert f'id="door-{edge.a[0]}-{edge.a[1]}-{edge.b[0]}-{edge.b[1]}"' in page
            assert f'data-color="{color}"' in page
        for color in layout.keys:
            assert f'id="key-{color}"' in page
        assert "<script" not in page and 'id="play"' not in page
        assert not EXTERNAL.search(page)
        assert render_html(dungeon) == page


def test_animation_embeds_the_frames_and_controls() -> None:
    for seed in DEV_SEEDS:
        dungeon = generate("L3", seed)
        frames = build_frames(dungeon, dungeon.solution.actions)
        page = render_html(dungeon, frames)
        assert _frames_json(page)["frames"] == [f.to_dict() for f in frames]
        for control in ("play", "prev", "next", "step", "speed", "agent", "trail", "fail"):
            assert f'id="{control}"' in page
        assert not EXTERNAL.search(page)
        assert render_html(dungeon, frames) == page


def test_embedded_json_cannot_close_the_script() -> None:
    dungeon = Dungeon.from_layout(chained_keys())
    frames = build_frames(dungeon, [Action("take", ("</script><b>",))])
    page = render_html(dungeon, frames)
    assert "</script><b>" not in page
    assert _frames_json(page)["frames"][1]["action"]["args"] == ["</script><b>"]  # type: ignore[index]


def test_player_template_ships_with_the_package() -> None:
    template = importlib.resources.files("apl.dungeon") / "assets" / "player.html"
    assert "{{SVG}}" in template.read_text(encoding="utf-8")


def test_step_table_shows_an_unknown_tool() -> None:
    dungeon = Dungeon.from_layout(chained_keys())
    frames = build_frames(dungeon, [Action("unknown", ("open",))])
    assert "unknown open" in render_text(dungeon, frames)


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_picture_has_one_room_rect_per_room(level: str) -> None:
    layout = generate(level, 1000).layout
    for animated in (False, True):
        drawing = svg(layout, animated)
        rects = re.findall(r'<rect class="room" id="room-(\d+)-(\d+)"', drawing)
        assert sorted((int(x), int(y)) for x, y in rects) == sorted(layout.rooms())
        # Above the drawing, below the agent: fog dims labels and keys, never the agent.
        if animated:
            assert drawing.rindex('class="room"') < drawing.index('id="trail"')
