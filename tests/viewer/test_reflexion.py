"""A4 in the viewer: offered on both problems, restarts as events (specs/007 US2)."""

from pathlib import Path

import pytest

from apl.dungeon import generate
from apl.survey import generate as generate_field
from tests.arch.test_reflexion import _a4, _gives_up_first
from tests.runner.scripted import scripted_factory, walk_field, walk_solution
from tests.viewer.test_app import OLLAMA, _body, _events, _start, _viewer


def test_reflexion_is_offered_on_both_problems(tmp_path: Path) -> None:  # acceptance 2.1
    data = _body(_viewer(tmp_path, architectures=None).options())
    assert "reflexion" in data["problems"]["dungeon"]["architectures"]
    assert "reflexion" in data["problems"]["survey"]["architectures"]


@pytest.mark.parametrize("level", ["L1", "S1"])
def test_a_restart_is_an_event_and_replays(tmp_path: Path, level: str) -> None:  # 2.2, 2.3
    survey = level.startswith("S")
    if survey:
        field = generate_field(level, 1000)
        play, start = walk_field(field.walk, total=field.true_total), list(field.start)
    else:
        dungeon = generate(level, 1000)
        play, start = walk_solution(dungeon), list(dungeon.layout.start)
    strategy = _a4(_gives_up_first(play))
    viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(strategy), architectures=None)
    episode_id = _start(
        viewer, "reflexion", level, 1000, **({"problem": "survey"} if survey else {})
    )
    events = _events(viewer, episode_id)
    types = [e["type"] for e in events]
    assert events[0]["data"]["attempts"] == 3  # the panel shows "Attempt 1 / 3" from the start
    restart = types.index("restart")
    roles = [e["data"]["role"] for e in events[:restart] if e["type"] == "turn"]
    assert roles == ["actor (attempt 1)", "reflector"]
    data = events[restart]["data"]
    assert data["attempt"] == 2 and data["frame"]["attempt"] == 2
    assert data["frame"]["position"] == start
    steps = [e["data"]["frame"] for e in events[restart:] if e["type"] == "step"]
    assert steps and all(f["attempt"] == 2 for f in steps)
    assert events[-1]["data"]["row"]["success"] and events[-1]["data"]["row"]["attempts"] == 2
    replayed = _viewer(tmp_path, OLLAMA).session(episode_id)
    assert replayed is not None and replayed.done
    assert [event for _, event in (x for x in replayed.stream() if x)] == events
