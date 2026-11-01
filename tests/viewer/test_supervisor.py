"""A5 in the viewer: offered on the dungeon only, its roles in the side panel (specs/008 US2)."""

from pathlib import Path

import pytest

from apl.dungeon import generate
from tests.arch.test_supervisor import split_walk
from tests.runner.scripted import scripted_factory
from tests.viewer.test_app import OLLAMA, _body, _events, _start, _viewer


def test_supervisor_is_offered_on_the_dungeon_only(tmp_path: Path) -> None:  # acceptance 2.1
    data = _body(_viewer(tmp_path, architectures=None).options())
    assert "supervisor" in data["problems"]["dungeon"]["architectures"]
    assert "supervisor" not in data["problems"]["survey"]["architectures"]


@pytest.mark.parametrize("level", ["L1", "L2", "L3"])  # SC-005
def test_the_side_panel_shows_each_job_and_replays_it(tmp_path: Path, level: str) -> None:
    solution = generate(level, 1000).solution.actions
    strategy = split_walk(level, 1000)
    viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(strategy), architectures=None)
    episode_id = _start(viewer, "supervisor", level, 1000)
    events = _events(viewer, episode_id)
    turns = [e["data"] for e in events if e["type"] == "turn"]
    roles = [t["role"] for t in turns]
    assert roles[:2] == ["supervisor", "navigator (task 1)"]  # acceptance 2.2, 2.3
    assert turns[0]["text"] == '{"to": "navigator", "task": "do the next move"}'
    helpers = {r.split(" (task ")[0] for r in roles if r != "supervisor"}
    owners = {"inventory" if a.tool in ("take", "use") else "navigator" for a in solution}
    assert helpers == owners  # the inventory helper works wherever the solution needs keys
    assert any(e["type"] == "step" for e in events)
    assert events[-1]["data"]["row"]["success"]
    replayed = _viewer(tmp_path, OLLAMA).session(episode_id)  # acceptance 2.4
    assert replayed is not None and replayed.done
    assert [event for _, event in (x for x in replayed.stream() if x)] == events
