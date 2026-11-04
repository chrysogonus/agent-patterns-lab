"""The signal trace in the viewer (specs/009 contracts/viewer.md, US1, SC-005)."""

import json
from pathlib import Path

from langchain_core.messages import AIMessage

from apl.signal_trace import generate
from apl.viewer.app import EPISODE_ID
from tests.runner.scripted import scripted_factory
from tests.viewer.test_app import OLLAMA, _body, _events, _start, _viewer


def test_options_and_the_pipe(tmp_path: Path) -> None:
    viewer = _viewer(tmp_path, architectures=None)
    signal = _body(viewer.options())["problems"]["signal"]
    assert signal["levels"] == ["T1", "T2", "T3", "T4"] and signal["dev_seeds"][0] == 1000
    assert set(signal["architectures"]) == {
        "react",
        "mapstate",
        "plan_execute",
        "reflexion",
        "retry",
        "hybrid",
    }
    pipe = generate("T2", 1000)
    data = _body(viewer.signal("T2", "1000"))
    assert data["problem"] == "signal" and data["segments"] == 64
    assert data["runs"] == [{"from": "S", "first": 1, "last": 64}]
    assert data["broken"] == pipe.broken and data["budget"] == 64
    assert data["optimal_steps"] == 7 and data["reference_is_optimal"]
    assert data["svg"].startswith("<svg") and data["svg"].count('data-seg="') == 64
    reference = data["solution"]
    assert reference[0]["answers"] == [] and len(reference[0]["suspects"]) == 64
    assert reference[-1]["submitted"] == pipe.broken and reference[-1]["suspects"] == [pipe.broken]
    t4 = _body(viewer.signal("T4", "1000"))
    assert t4["segments"] == 256 and t4["budget"] == 256 and not t4["reference_is_optimal"]
    assert t4["svg"].count('data-seg="') == 256
    assert viewer.signal("T2", "2000")[0] == 403
    assert viewer.signal("T9", "1000")[0] == 400


def test_an_architecture_that_does_not_play_it_is_refused(tmp_path: Path) -> None:
    viewer = _viewer(tmp_path, OLLAMA, architectures=None)
    status, _, body = viewer.start_episode(
        {"arch": "fanout", "level": "T1", "seed": 1000, "problem": "signal"}
    )
    assert status == 400 and b"fanout does not play the signal problem" in body


def test_a_hybrid_episode_streams_signal_frames_and_replays(tmp_path: Path) -> None:
    pipe = generate("T2", 1000)
    factory = scripted_factory(lambda messages: AIMessage("1"))
    viewer = _viewer(tmp_path, OLLAMA, model_factory=factory, architectures=None)
    episode_id = _start(viewer, "hybrid", "T2", 1000, problem="signal")
    events = _events(viewer, episode_id)
    start = events[0]["data"]
    assert start["problem"] == "signal" and start["segments"] == 64
    assert start["broken"] == pipe.broken and start["optimal_steps"] == 7
    steps = [e["data"] for e in events if e["type"] == "step"]
    assert steps and steps[0]["frame"]["answers"] == [[32, pipe.wet(32)]]
    frame = steps[-1]["frame"]
    assert frame["submitted"] == pipe.broken and frame["suspects"] == [pipe.broken]
    assert frame["probes"] == len(steps) - 1 and frame["wasted"] == 0
    assert set(frame) >= {"step", "action", "ok", "error", "end_reason", "answers", "suspects"}
    row = events[-1]["data"]["row"]
    assert row["problem"] == "signal" and row["success"]
    saved = json.loads((tmp_path / "viewer" / episode_id / "episode.json").read_text())
    assert saved["problem"] == "signal"
    replayed = _viewer(tmp_path, OLLAMA).session(episode_id)
    assert replayed is not None and replayed.done
    assert [event for _, event in (x for x in replayed.stream() if x)] == events


def test_a_hybrid_episode_on_t4_streams_and_replays(tmp_path: Path) -> None:  # specs/013 SC-005
    pipe = generate("T4", 1000)
    factory = scripted_factory(lambda messages: AIMessage("1"))
    viewer = _viewer(tmp_path, OLLAMA, model_factory=factory, architectures=None)
    episode_id = _start(viewer, "hybrid", "T4", 1000, problem="signal")
    assert EPISODE_ID.fullmatch(episode_id)  # the id names the level: T4 is a valid one
    events = _events(viewer, episode_id)
    assert events[0]["data"]["segments"] == 256
    frame = [e["data"] for e in events if e["type"] == "step"][-1]["frame"]
    assert frame["submitted"] == pipe.broken and frame["suspects"] == [pipe.broken]
    row = events[-1]["data"]["row"]
    assert row["level"] == "T4" and row["success"]
    replayed = _viewer(tmp_path, OLLAMA).session(episode_id)
    assert replayed is not None and replayed.done
    assert [event for _, event in (x for x in replayed.stream() if x)] == events
