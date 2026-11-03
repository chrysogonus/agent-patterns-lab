"""The rune floor in the viewer (specs/010 contracts/viewer.md, US1, SC-005)."""

import json
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.reflexion import REFLECTOR_INSTRUCTIONS
from apl.rune import generate
from apl.rune.rules import describe
from apl.viewer.app import EPISODE_ID
from tests.arch.rune_play import reference_calls
from tests.arch.test_reflexion_rune import _straight_row_trap
from tests.runner.scripted import by_system, play_calls, scripted_factory, tool_calls
from tests.viewer.test_app import OLLAMA, _body, _events, _start, _viewer

FRAME_KEYS = {
    "step", "action", "ok", "error", "end_reason", "position", "walk", "walks", "traps",
    "traps_count", "repeated", "walk_number",
}  # fmt: skip


def test_options_and_the_floor(tmp_path: Path) -> None:
    viewer = _viewer(tmp_path, architectures=None)
    rune = _body(viewer.options())["problems"]["rune"]
    assert rune["levels"] == ["R0", "R1", "R2", "R3"] and rune["dev_seeds"][0] == 1000
    assert set(rune["architectures"]) == {
        "react",
        "mapstate",
        "plan_execute",
        "reflexion",
        "retry",
        "hybrid",
    }
    floor = generate("R1", 1000)
    data = _body(viewer.rune("R1", "1000"))
    assert data["problem"] == "rune" and (data["columns"], data["rows"]) == (7, 5)
    assert data["start"] == "A3" and data["goal"] == "G3" and len(data["floor"]) == 5
    assert data["rule"] == describe(floor.rule)
    assert data["budget"] == floor.budget and data["optimal_steps"] == floor.reference
    assert data["reference_is_optimal"]
    assert data["svg"].startswith("<svg") and data["svg"].count('data-cell="') == 35
    reference = data["solution"]
    assert reference[0]["position"] == "A3" and reference[0]["walk"] == []
    assert reference[-1]["end_reason"] == "goal" and len(reference) == floor.reference + 1
    assert set(reference[0]) >= FRAME_KEYS
    assert viewer.rune("R1", "2000")[0] == 403
    assert viewer.rune("R9", "1000")[0] == 400


def test_an_architecture_that_does_not_play_it_is_refused(tmp_path: Path) -> None:
    viewer = _viewer(tmp_path, OLLAMA, architectures=None)
    status, _, body = viewer.start_episode(
        {"arch": "fanout", "level": "R1", "seed": 1000, "problem": "rune"}
    )
    assert status == 400 and b"fanout does not play the rune problem" in body


def test_a_react_episode_streams_rune_frames_and_replays(tmp_path: Path) -> None:
    factory = scripted_factory(play_calls(reference_calls("R1", 1000)))
    viewer = _viewer(tmp_path, OLLAMA, model_factory=factory, architectures=None)
    episode_id = _start(viewer, "react", "R1", 1000, problem="rune")
    assert EPISODE_ID.fullmatch(episode_id)
    events = _events(viewer, episode_id)
    start = events[0]["data"]
    assert start["problem"] == "rune" and (start["columns"], start["rows"]) == (7, 5)
    assert start["start"] == "A3" and start["goal"] == "G3"
    steps = [e["data"] for e in events if e["type"] == "step"]
    assert steps and set(steps[0]["frame"]) >= FRAME_KEYS
    assert steps[0]["frame"]["walk"] == [steps[0]["frame"]["position"]]
    assert steps[-1]["frame"]["end_reason"] == "goal"
    row = events[-1]["data"]["row"]
    assert row["problem"] == "rune" and row["success"] and row["traps"] == 0
    saved = json.loads((tmp_path / "viewer" / episode_id / "episode.json").read_text())
    assert saved["problem"] == "rune"
    replayed = _viewer(tmp_path, OLLAMA).session(episode_id)
    assert replayed is not None and replayed.done
    assert [event for _, event in (x for x in replayed.stream() if x)] == events


def test_a_reflexion_trap_emits_one_restart(tmp_path: Path) -> None:
    right = reference_calls("R1", 1000)
    trap_after = _straight_row_trap("R1", 1000)

    def actor(messages: list[BaseMessage]) -> AIMessage:
        text = "\n".join(str(m.content) for m in messages)
        if "Attempt 1 of 3." in text:
            return tool_calls(*[("move", {"direction": "east"})] * trap_after)
        return tool_calls(*right)

    strategy = by_system({REFLECTOR_INSTRUCTIONS: lambda m: AIMessage("note")}, actor)
    viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(strategy), architectures=None)
    episode_id = _start(viewer, "reflexion", "R1", 1000, problem="rune")
    events = _events(viewer, episode_id)
    assert [e["type"] for e in events].count("restart") == 1
    trap_frame = next(e["data"]["frame"] for e in events if e["type"] == "step")
    assert trap_frame is not None
    row = events[-1]["data"]["row"]
    assert row["success"] and row["traps"] == 1 and row["attempts"] == 2
