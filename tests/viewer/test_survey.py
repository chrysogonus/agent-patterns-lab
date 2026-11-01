"""The viewer on the survey field (specs/005 US1, contracts/viewer.md)."""

import json
from pathlib import Path

from apl.runner import registry
from apl.survey import generate
from tests.arch.test_survey_archs import _fanout
from tests.runner.scripted import scripted_factory, walk_field
from tests.viewer.test_app import OLLAMA, _body, _events, _start, _viewer

FIELD = generate("S1", 1000)


def test_options_list_the_problems_and_who_plays_them(tmp_path: Path) -> None:
    archs = {name: registry.load(name) for name in ("react", "hybrid", "fanout")}
    data = _body(_viewer(tmp_path, architectures=archs).options())
    assert data["levels"] == ["L1", "L2", "L3"]  # the dungeon's fields stay as they were
    assert set(data["problems"]) == {"dungeon", "survey"}
    survey = data["problems"]["survey"]
    assert survey["levels"] == ["S1", "S2", "S3"] and survey["test_seeds"] == [2000, 2019]
    assert survey["architectures"] == ["fanout", "react"]
    assert data["problems"]["dungeon"]["architectures"] == ["fanout", "hybrid", "react"]


def test_a_survey_board(tmp_path: Path) -> None:
    viewer = _viewer(tmp_path)
    data = _body(viewer.survey("S1", "1000"))
    assert data["problem"] == "survey" and data["true_total"] == 6 and data["size"] == 6
    assert data["optimal_steps"] == 36 and data["budget"] == 108
    assert data["svg"].count('class="room"') == 36 and 'id="agent"' in data["svg"]
    assert len(data["solution"]) == 36 and data["solution"][-1]["position"] == [0, 5]
    assert viewer.survey("S1", "2000")[0] == 403
    assert viewer.survey("L1", "1000")[0] == 400


def test_an_architecture_that_does_not_play_the_survey_is_refused(tmp_path: Path) -> None:
    viewer = _viewer(tmp_path, architectures={"hybrid": registry.load("hybrid")})
    status, _, body = viewer.start_episode(
        {"problem": "survey", "arch": "hybrid", "level": "S1", "seed": 1000}
    )
    assert status == 400
    assert (
        json.loads(body)["error"] == "hybrid does not play the survey problem (it plays: dungeon)"
    )
    status, _, _ = viewer.start_episode(
        {"problem": "chess", "arch": "hybrid", "level": "S1", "seed": 1}
    )
    assert status == 400


def test_a_survey_episode_streams_frames_with_the_tally(tmp_path: Path) -> None:
    viewer = _viewer(
        tmp_path, OLLAMA, model_factory=scripted_factory(walk_field(FIELD.walk, total=6)),
        architectures={"react": registry.load("react")},
    )  # fmt: skip
    episode_id = _start(viewer, "react", "S1", 1000, problem="survey")
    assert "-react-S1-1000" in episode_id
    events = _events(viewer, episode_id)
    start, end = events[0]["data"], events[-1]["data"]
    assert start["problem"] == "survey" and start["true_total"] == 6 and start["budget"] == 108
    steps = [e["data"]["frame"] for e in events if e["type"] == "step"]
    assert len(steps) == 36 and steps[0]["position"] == [1, 0]
    assert [f["deposits_seen"] for f in steps][-2] == 6 and steps[-1]["submitted"] == 6
    assert steps[-1]["end_reason"] == "submitted"
    assert end["row"]["problem"] == "survey" and end["row"]["success"]
    assert end["row"]["submitted_total"] == 6
    # Saved and listed with its problem, so the page reopens the right world.
    listed = _body(viewer.list_episodes())
    assert listed[0]["id"] == episode_id and listed[0]["problem"] == "survey"
    saved = viewer.session(episode_id)
    assert saved is not None and saved.events == events


def test_four_scouts_on_the_field(tmp_path: Path) -> None:
    plan = {"scouts": [{"task": "walk", "steps": 40}, {"task": "walk", "steps": 40}]}
    viewer = _viewer(
        tmp_path, OLLAMA, model_factory=scripted_factory(_fanout(plan, {"total": 6})),
        architectures={"fanout": registry.load("fanout")},
    )  # fmt: skip
    events = _events(viewer, _start(viewer, "fanout", "S1", 1000, problem="survey"))
    frames = [e["data"]["frame"] for e in events if e["type"] == "step"]
    assert all(len(f["scouts"]) == 2 for f in frames)
    assert frames[-1]["submitted"] == 6 and events[-1]["data"]["row"]["success"]


def test_scout_3_lifts_the_fog_in_its_own_color(tmp_path: Path) -> None:  # US1/AC2
    from tests.arch.test_survey_archs import FIELD2, four_scouts

    viewer = _viewer(
        tmp_path, OLLAMA, model_factory=scripted_factory(four_scouts(FIELD2.true_total)),
        architectures={"rounds": registry.load("rounds")},
    )  # fmt: skip
    events = _events(viewer, _start(viewer, "rounds", "S2", 1000, problem="survey"))
    steps = [e["data"] for e in events if e["type"] == "step"]
    before = 0
    found = []
    for step in steps:
        frame = step["frame"]
        if step["scout"] == 3 and frame["deposits_seen"] == before + 1:
            found.append(tuple(frame["scouts"][3]["position"]))
        before = frame["deposits_seen"]
    assert found and all(cell in FIELD2.deposits for cell in found)
    assert events[-1]["data"]["row"]["success"]
