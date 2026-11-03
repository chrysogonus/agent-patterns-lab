"""The workshop in the viewer (specs/011 contracts/viewer.md, US1, SC-005)."""

import json
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.reflexion import REFLECTOR_INSTRUCTIONS
from apl.viewer.app import EPISODE_ID
from apl.workshop import generate
from apl.workshop.plans import greedy_calls, reference_calls
from tests.runner.scripted import by_system, play_calls, scripted_factory, tool_calls
from tests.viewer.test_app import OLLAMA, _body, _events, _start, _viewer

FRAME_KEYS = {
    "step", "action", "ok", "error", "end_reason", "stock", "inventory", "inspected", "crafted",
    "wasted",
}  # fmt: skip


def test_options_and_the_workshop(tmp_path: Path) -> None:
    viewer = _viewer(tmp_path, architectures=None)
    workshop = _body(viewer.options())["problems"]["workshop"]
    assert workshop["levels"] == ["W1", "W2", "W3"] and workshop["dev_seeds"][0] == 1000
    assert set(workshop["architectures"]) == {
        "react", "mapstate", "plan_execute", "reflexion", "retry", "supervisor", "hybrid",
    }  # fmt: skip
    w = generate("W2", 1000)
    data = _body(viewer.workshop("W2", "1000"))
    assert data["problem"] == "workshop" and data["goal"] == w.goal
    assert data["stock"] == dict(w.stock) and data["scarce"] == sorted(w.scarce)
    assert data["recipes"] == {k: [list(r) for r in v] for k, v in w.recipes.items()}
    assert data["reference_choice"] == dict(w.reference_choice)
    assert data["budget"] == w.budget and data["optimal_steps"] == w.reference
    assert data["svg"].startswith("<svg") and 'id="badges"' in data["svg"]
    reference = data["solution"]
    assert set(reference[0]) >= FRAME_KEYS and reference[-1]["end_reason"] == "goal"
    assert len(reference) == w.reference + 1
    assert viewer.workshop("W2", "2000")[0] == 403
    assert viewer.workshop("W9", "1000")[0] == 400


def test_an_architecture_that_does_not_play_it_is_refused(tmp_path: Path) -> None:
    viewer = _viewer(tmp_path, OLLAMA, architectures=None)
    status, _, body = viewer.start_episode(
        {"arch": "fanout", "level": "W1", "seed": 1000, "problem": "workshop"}
    )
    assert status == 400 and b"fanout does not play the workshop problem" in body


def test_a_react_episode_streams_workshop_frames_and_replays(tmp_path: Path) -> None:
    w = generate("W2", 1000)
    factory = scripted_factory(play_calls(reference_calls(w)))
    viewer = _viewer(tmp_path, OLLAMA, model_factory=factory, architectures=None)
    episode_id = _start(viewer, "react", "W2", 1000, problem="workshop")
    assert EPISODE_ID.fullmatch(episode_id)
    events = _events(viewer, episode_id)
    start = events[0]["data"]
    assert start["problem"] == "workshop" and start["goal"] == w.goal
    assert start["stock"] == dict(w.stock) and start["scarce"] == sorted(w.scarce)
    steps = [e["data"] for e in events if e["type"] == "step"]
    assert steps and set(steps[0]["frame"]) >= FRAME_KEYS
    assert steps[0]["frame"]["inspected"] == [w.goal]
    assert steps[-1]["frame"]["end_reason"] == "goal"
    row = events[-1]["data"]["row"]
    assert row["problem"] == "workshop" and row["success"] and row["wasted"] == 0
    saved = json.loads((tmp_path / "viewer" / episode_id / "episode.json").read_text())
    assert saved["problem"] == "workshop"
    replayed = _viewer(tmp_path, OLLAMA).session(episode_id)
    assert replayed is not None and replayed.done
    assert [event for _, event in (x for x in replayed.stream() if x)] == events


def test_a_reflexion_episode_that_gets_stuck_emits_one_restart(tmp_path: Path) -> None:
    w = generate("W2", 1000)

    def actor(messages: list[BaseMessage]) -> AIMessage:
        text = "\n".join(str(m.content) for m in messages)
        calls = greedy_calls(w) if "Attempt 1 of 3." in text else reference_calls(w)
        return tool_calls(*calls)

    strategy = by_system({REFLECTOR_INSTRUCTIONS: lambda m: AIMessage("note")}, actor)
    viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(strategy), architectures=None)
    episode_id = _start(viewer, "reflexion", "W2", 1000, problem="workshop")
    events = _events(viewer, episode_id)
    assert [e["type"] for e in events].count("restart") == 1
    row = events[-1]["data"]["row"]
    assert row["success"] and row["stuck"] is False and row["attempts"] == 2 and row["wasted"] == 1
