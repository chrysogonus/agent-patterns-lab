"""What robots can and cannot learn from the warehouse's results (specs/012 T009)."""

import json
import random
from dataclasses import replace
from typing import Any

import pytest

from apl.warehouse import DEV_SEEDS, LEVELS, generate, start_episode
from apl.warehouse.model import parse_cell
from apl.warehouse.tools import AgentTools

SHAPES = [
    {"cell", "corridors", "packages_seen", "carrying", "on_drop", "delivered", "packages",
     "columns", "rows"},
    {"picked", "cell"},
    {"delivered_package", "delivered", "packages"},
]  # fmt: skip


@pytest.mark.parametrize("level", sorted(LEVELS))
@pytest.mark.parametrize("seed", DEV_SEEDS)
def test_random_calls_keep_the_envelope_and_show_only_what_is_seen(level: str, seed: int) -> None:
    floor = generate(level, seed)
    episode = start_episode(floor)
    rng = random.Random(seed)
    for _ in range(3):
        episode.add_scout()
    for _ in range(300):
        if episode.end_reason is not None:
            break
        robot = rng.randrange(4)
        choice = rng.choice(["look", "move", "move", "move", "pick", "drop", "unknown"])
        if choice == "move":
            result = episode.move(rng.choice(["north", "east", "south", "west", "up"]), scout=robot)
        elif choice == "unknown":
            result = episode.unknown("push", scout=robot)
        else:
            result = getattr(episode, choice)(scout=robot)
        found: dict[str, Any] = result.to_dict()
        assert set(found) == {"ok", "error", "data"}
        text = json.dumps(found)
        assert "reference" not in text and "budget" not in text
        if not found["ok"]:
            assert set(found["error"]) == {"code", "message"} and found["data"] is None
            continue
        data = found["data"]
        assert set(data) in SHAPES
        if "packages_seen" in data:
            visible = {c for name in data["corridors"] for c in floor.corridor_cells(name)}
            assert all(parse_cell(p["cell"]) in visible for p in data["packages_seen"])


def test_the_start_view_hides_where_the_packages_are() -> None:
    floor = generate("P2", 1000)
    moved = tuple((n, (c[0], (c[1] + 2) % floor.rows)) for n, c in floor.packages)
    other = replace(floor, packages=moved)
    assert start_episode(floor).start_view() == start_episode(other).start_view()


def test_agent_tools_expose_only_the_tools() -> None:
    public = {n for n in dir(AgentTools) if not n.startswith("_")}
    assert public == {"start", "look", "move", "pick", "drop"}
