"""Text map, route overlay, and HTML picture (SC-010, SC-011, FR-024 to FR-028)."""

import importlib.resources
import json
import re

import pytest

from apl.dungeon import DEV_SEEDS, LEVELS, generate
from apl.dungeon.frames import build_frames
from apl.dungeon.model import Action, Dungeon
from apl.dungeon.render_html import render_html
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


def test_overlay_marks_the_route_and_lists_steps() -> None:
    for seed in DEV_SEEDS:
        dungeon = generate("L3", seed)
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
