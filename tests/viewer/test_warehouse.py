"""The warehouse in the viewer (specs/012 contracts/viewer.md, US1, SC-005)."""

import json
from pathlib import Path

from apl.arch.fanout import WAREHOUSE_FANOUT_INSTRUCTIONS
from apl.viewer.app import EPISODE_ID
from apl.warehouse import generate
from apl.warehouse.plans import blind_split
from tests.arch.warehouse_play import robot_actions, robots
from tests.runner.scripted import by_system, json_answer, scripted_factory
from tests.viewer.test_app import OLLAMA, _body, _events, _start, _viewer

FRAME_KEYS = {
    "step", "action", "ok", "error", "position", "end_reason", "seen", "packages", "delivered",
    "parallel_turns", "idle_robot_turns",
}  # fmt: skip


def test_options_and_the_warehouse(tmp_path: Path) -> None:
    viewer = _viewer(tmp_path, architectures=None)
    problem = _body(viewer.options())["problems"]["warehouse"]
    assert problem["levels"] == ["P1", "P2", "P3"] and problem["dev_seeds"][0] == 1000
    assert set(problem["architectures"]) == {"react", "mapstate", "fanout", "rounds", "blackboard"}
    assert set(problem["about"]) == set(problem["architectures"])
    floor = generate("P2", 1000)
    data = _body(viewer.warehouse("P2", "1000"))
    assert data["problem"] == "warehouse" and data["packages"] == 3
    assert (data["columns"], data["rows"]) == (9, 5)
    assert data["budget"] == floor.budget and data["optimal_steps"] == floor.reference_steps
    assert data["reference_is_optimal"] is False
    assert data["svg"].startswith("<svg") and 'id="agent"' in data["svg"]
    reference = data["solution"]
    assert set(reference[0]) >= FRAME_KEYS and reference[-1]["end_reason"] == "delivered"
    assert len(reference) == floor.reference_steps + 1
    assert viewer.warehouse("P2", "2000")[0] == 403
    assert viewer.warehouse("P9", "1000")[0] == 400


def test_an_architecture_that_does_not_play_it_is_refused(tmp_path: Path) -> None:
    viewer = _viewer(tmp_path, OLLAMA, architectures=None)
    status, _, body = viewer.start_episode(
        {"arch": "hybrid", "level": "P1", "seed": 1000, "problem": "warehouse"}
    )
    assert status == 400 and b"hybrid does not play the warehouse problem" in body


def test_a_fanout_episode_streams_robot_frames_and_replays(tmp_path: Path) -> None:
    actions = robot_actions(blind_split(generate("P2", 1000)))
    tasks = [{"task": f"share {n}", "steps": len(a) + 5} for n, a in actions.items()]
    strategy = by_system(
        {WAREHOUSE_FANOUT_INSTRUCTIONS: json_answer({"scouts": tasks})}, robots(actions)
    )
    viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(strategy), architectures=None)
    episode_id = _start(viewer, "fanout", "P2", 1000, problem="warehouse")
    assert EPISODE_ID.fullmatch(episode_id)
    events = _events(viewer, episode_id)
    start = events[0]["data"]
    assert start["problem"] == "warehouse" and start["packages"] == 3
    assert (start["columns"], start["rows"]) == (9, 5)
    steps = [e["data"] for e in events if e["type"] == "step"]
    frame = steps[-1]["frame"]
    assert set(frame) >= FRAME_KEYS and frame["delivered"] == 3
    assert len(frame["scouts"]) == 3 and all("carrying" in s for s in frame["scouts"])
    assert frame["idle_robot_turns"] > 0
    carried = [p for s in steps for p in s["frame"]["packages"] if p["carrier"] is not None]
    assert carried and all(p["cell"] is not None for p in carried)
    row = events[-1]["data"]["row"]
    assert row["success"] and row["delivered"] == 3 and row["idle_robot_turns"] > 0
    replayed = _viewer(tmp_path, OLLAMA).session(episode_id)
    assert replayed is not None and replayed.done
    assert [event for _, event in (x for x in replayed.stream() if x)] == events
    assert json.dumps(row)
