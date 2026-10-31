"""The viewer's request logic, called without sockets (contracts/viewer-api.md)."""

import json
import re
import threading
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from apl.dungeon import DEV_SEEDS, generate
from apl.dungeon.frames import parse_route_file
from apl.dungeon.model import Direction
from apl.runner.episode import play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.viewer.app import Viewer
from tests.runner import loop_arch
from tests.runner.scripted import (
    FakeProviderError,
    Strategy,
    bump_wall,
    raise_error,
    replay_solution,
    scripted_factory,
    text_answer,
    then,
)

ARCHS = {"react": loop_arch.play, "mapstate": loop_arch.play}


def _viewer(tmp_path: Path, settings: Settings | None = None, **kwargs: Any) -> Viewer:
    return Viewer(
        settings or Settings(num_ctx=8192),
        results_dir=tmp_path / "viewer",
        model_factory=kwargs.pop("model_factory", scripted_factory(text_answer())),
        architectures=kwargs.pop("architectures", ARCHS),
        **kwargs,
    )


def _body(response: tuple[int, str, bytes]) -> Any:
    status, content_type, body = response
    assert content_type == "application/json"
    return json.loads(body)


def test_options(tmp_path: Path) -> None:
    status, _, _ = response = _viewer(tmp_path).options()
    data = _body(response)
    assert status == 200
    assert data["levels"] == ["L1", "L2", "L3"]
    assert data["dev_seeds"] == list(DEV_SEEDS)
    assert data["test_seeds"] == [2000, 2019]
    assert data["architectures"] == ["mapstate", "react"]
    assert data["model"] == "vllm:qwen3.5-9b" and data["settings"]["num_ctx"] == 8192
    assert data["can_run"] is True and data["cannot_run_reason"] is None
    assert data["models"] == [{"name": "vllm:qwen3.5-9b", "cannot_run_reason": None}]


def test_options_list_only_written_architectures(tmp_path: Path) -> None:
    viewer = Viewer(Settings(), results_dir=tmp_path)  # the real registry
    assert "react" in _body(viewer.options())["architectures"]


@pytest.mark.parametrize(
    ("model", "execute", "can_run"),
    [
        ("vllm:qwen3.5-9b", False, True),
        ("ollama:qwen3:8b", False, True),
        ("openai:gpt-6-luna", False, False),
        ("openai:gpt-6-luna", True, True),
    ],
)
def test_paid_providers_need_execute(
    tmp_path: Path, model: str, execute: bool, can_run: bool
) -> None:
    data = _body(_viewer(tmp_path, Settings(model=model), execute=execute).options())
    assert data["can_run"] is can_run
    assert (data["cannot_run_reason"] is None) is can_run


def test_dungeon(tmp_path: Path) -> None:
    viewer = _viewer(tmp_path)
    status, _, body = viewer.dungeon("L3", "1000")
    data = json.loads(body)
    dungeon = generate("L3", 1000)
    assert status == 200
    assert data["level"] == "L3" and data["seed"] == 1000 and data["size"] == 5
    assert data["budget"] == dungeon.budget and data["optimal_steps"] == dungeon.solution.length
    assert data["start"] == list(dungeon.layout.start) and data["exit"] == list(dungeon.layout.exit)
    assert data["cell"] > 0 and data["margin"] > 0 and data["svg"].startswith("<svg")
    solution = data["solution"]
    assert len(solution) == dungeon.solution.length + 1
    assert solution[0]["position"] == data["start"] and solution[-1]["position"] == data["exit"]
    assert viewer.dungeon("L3", "1000") == (status, "application/json", body)  # SC-001
    assert viewer.dungeon("L3", "4242")[0] == 200  # outside both seed sets: allowed


@pytest.mark.parametrize(
    ("level", "seed", "status", "message"),
    [
        ("L1", "2003", 403, "test seed"),
        ("L1", "-1", 400, "seed"),
        ("L1", "abc", 400, "seed"),
        ("L1", "1.5", 400, "seed"),
        ("L9", "1000", 400, "level"),
    ],
)
def test_bad_dungeon_requests(
    tmp_path: Path, level: str, seed: str, status: int, message: str
) -> None:
    response = _viewer(tmp_path).dungeon(level, seed)
    assert response[0] == status and message in _body(response)["error"]


# ---------- episodes (User Story 2) ----------

OLLAMA = Settings(model="ollama:qwen3:8b")  # local, and needs no server lookup in tests


def _events(viewer: Viewer, episode_id: str) -> list[dict[str, Any]]:
    session = viewer.session(episode_id)
    assert session is not None
    list(session.stream())  # blocks until the episode has ended
    return session.events


def _start(
    viewer: Viewer, arch: str = "react", level: str = "L1", seed: int = 1000, **extra: object
) -> str:
    status, _, body = viewer.start_episode({"arch": arch, "level": level, "seed": seed, **extra})
    assert status == 201, body
    episode_id: str = json.loads(body)["id"]
    return episode_id


def test_episode_events_in_order(tmp_path: Path) -> None:
    dungeon = generate("L1", 1000)
    viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(replay_solution(dungeon)))
    episode_id = _start(viewer)
    assert re.fullmatch(r"\d{8}-\d{6}-react-L1-1000(-\d+)?", episode_id)
    events = _events(viewer, episode_id)
    types = [e["type"] for e in events]
    assert types[0] == "start" and types[-1] == "end"
    start = events[0]["data"]
    assert start["arch"] == "react" and start["level"] == "L1" and start["seed"] == 1000
    assert start["budget"] == dungeon.budget and start["frame"]["position"] == list(
        dungeon.layout.start
    )
    # Each thinking is followed by its turn, then by that turn's steps.
    calls = [e["data"]["call"] for e in events if e["type"] in ("thinking", "turn", "step")]
    assert calls == sorted(calls)
    for i, event in enumerate(events):
        if event["type"] == "thinking":
            assert events[i + 1]["type"] == "turn"
    steps = [e["data"] for e in events if e["type"] == "step"]
    assert len(steps) == dungeon.solution.length
    assert steps[-1]["frame"]["position"] == list(dungeon.layout.exit)
    end = events[-1]["data"]
    assert end["row"]["success"] is True and end["row"]["arch"] == "react"
    folder = tmp_path / "viewer" / episode_id
    assert end["saved"] == str(folder)
    for name in ("events.jsonl", "outcome.json", "conversation.json", "episode.json"):
        assert (folder / name).is_file(), name
    saved = json.loads((folder / "episode.json").read_text())
    assert saved["row"] == end["row"] and saved["settings"]["model"] == "ollama:qwen3:8b"
    assert {"code", "versions", "started", "ended"} <= set(saved)


def _blocking(release: threading.Event, then: Strategy) -> Strategy:
    def strategy(messages: list[BaseMessage]) -> AIMessage:
        release.wait(timeout=10)
        return then(messages)

    return strategy


def test_one_episode_at_a_time_and_the_running_one_is_listed(tmp_path: Path) -> None:
    release = threading.Event()
    viewer = _viewer(
        tmp_path, OLLAMA, model_factory=scripted_factory(_blocking(release, text_answer()))
    )
    episode_id = _start(viewer)
    listed = _body(viewer.list_episodes())
    assert listed[0]["id"] == episode_id and listed[0]["running"] is True  # FR-014
    status, _, body = viewer.start_episode({"arch": "react", "level": "L1", "seed": 1001})
    assert status == 409 and json.loads(body)["running"] == episode_id
    release.set()
    assert _events(viewer, episode_id)[-1]["data"]["row"]["end_reason"] == "stopped"
    assert viewer.start_episode({"arch": "react", "level": "L1", "seed": 1001})[0] == 201


def test_stop_ends_the_episode_after_the_current_turn(tmp_path: Path) -> None:
    release = threading.Event()
    wall = _wall_of_start("L1", 1000)
    factory = scripted_factory(_blocking(release, bump_wall(wall)))
    viewer = _viewer(tmp_path, OLLAMA, model_factory=factory)
    episode_id = _start(viewer)
    session = viewer.session(episode_id)
    assert session is not None
    for item in session.stream():  # wait until the first model call is under way
        if item is not None and item[1]["type"] == "thinking":
            break
    assert viewer.stop_episode(episode_id)[0] == 202
    assert viewer.stop_episode(episode_id)[0] == 202  # stopping twice is fine
    release.set()
    events = _events(viewer, episode_id)
    assert "stopping" in [e["type"] for e in events]
    row = events[-1]["data"]["row"]
    assert row["end_reason"] == "stopped" and row["steps"] == 0  # the turn's call never ran
    assert viewer.stop_episode("20990101-000000-react-L1-1000")[0] == 404


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"arch": "react", "level": "L1", "seed": 2001}, 403),
        ({"arch": "nope", "level": "L1", "seed": 1000}, 400),
        ({"arch": "react", "level": "L7", "seed": 1000}, 400),
        ({"arch": "react", "level": "L1", "seed": -3}, 400),
        ({"arch": "react", "level": "L1"}, 400),
        ("not an object", 400),
    ],
)
def test_bad_episode_requests(tmp_path: Path, body: object, status: int) -> None:
    assert _viewer(tmp_path, OLLAMA).start_episode(body)[0] == status


def test_paid_provider_without_execute_cannot_start(tmp_path: Path) -> None:
    viewer = _viewer(tmp_path, Settings(model="openai:gpt-6-luna"))
    status, _, body = viewer.start_episode({"arch": "react", "level": "L1", "seed": 1000})
    assert status == 403 and "apl serve --execute" in json.loads(body)["error"]  # SC-005


def test_the_page_can_switch_models(tmp_path: Path) -> None:
    luna = Settings(model="openai:gpt-6-luna")
    models = {
        "ollama:qwen3:8b": Settings(model="ollama:qwen3:8b", num_ctx=1),
        "openai:gpt-6-luna": luna,
    }
    viewer = _viewer(tmp_path, OLLAMA, models=models)
    offered = _body(viewer.options())["models"]
    assert [m["name"] for m in offered] == ["ollama:qwen3:8b", "openai:gpt-6-luna"]  # default first
    assert (
        offered[0]["cannot_run_reason"] is None and "--execute" in offered[1]["cannot_run_reason"]
    )
    body = {"arch": "react", "level": "L1", "seed": 1000}
    assert viewer.start_episode({**body, "model": "openai:gpt-6-luna"})[0] == 403
    assert viewer.start_episode({**body, "model": "anthropic:x"})[0] == 400
    assert viewer.start_episode({**body, "model": 3})[0] == 400
    viewer.execute = True
    start = _events(viewer, _start(viewer, model="openai:gpt-6-luna"))[0]["data"]
    assert start["model"] == "openai:gpt-6-luna" and start["settings"] == luna.record()
    assert _body(viewer.list_episodes())[0]["model"] == "openai:gpt-6-luna"
    default = _events(viewer, _start(viewer))[0]["data"]  # no model given: the default
    assert default["settings"] == OLLAMA.record()  # not the offered copy with num_ctx=1


def test_provider_failure_is_shown_and_the_viewer_stays_usable(tmp_path: Path) -> None:
    strategy = then(raise_error(FakeProviderError(503)), 1, text_answer())
    viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(strategy))
    end = _events(viewer, _start(viewer))[-1]["data"]
    assert end["row"]["status"] == "error" and "503" in end["row"]["error"]  # FR-017
    assert _events(viewer, _start(viewer, seed=1001))[-1]["data"]["row"]["status"] == "completed"


def test_permanent_provider_error_ends_the_episode(tmp_path: Path) -> None:
    viewer = _viewer(
        tmp_path, OLLAMA, model_factory=scripted_factory(raise_error(FakeProviderError(401)))
    )
    end = _events(viewer, _start(viewer))[-1]["data"]
    assert end["row"] is None and "HTTP 401" in end["error"]


def _wall_of_start(level: str, seed: int) -> str:
    layout = generate(level, seed).layout
    return next(str(d) for d in Direction if layout.door(layout.start, d) is None)


def test_shutdown_stops_and_saves_the_running_episode(tmp_path: Path) -> None:
    release = threading.Event()
    factory = scripted_factory(_blocking(release, bump_wall(_wall_of_start("L1", 1000))))
    viewer = _viewer(tmp_path, OLLAMA, model_factory=factory)
    episode_id = _start(viewer)
    threading.Timer(0.2, release.set).start()
    viewer.shutdown(timeout=10)  # what Ctrl-C in `apl serve` does
    session = viewer.session(episode_id)
    assert session is not None and session.done
    assert session.events[-1]["data"]["row"]["end_reason"] == "stopped"
    assert (tmp_path / "viewer" / episode_id / "episode.json").is_file()


# ---------- saved episodes (User Story 4) ----------


def test_saved_episodes_are_listed_newest_first(tmp_path: Path) -> None:
    dungeon = generate("L1", 1000)
    viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(replay_solution(dungeon)))
    first = _start(viewer)
    _events(viewer, first)
    second_viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(text_answer()))
    second = _start(second_viewer, seed=1001)
    _events(second_viewer, second)
    (tmp_path / "viewer" / "junk").mkdir()  # not an episode: skipped
    listed = _body(second_viewer.list_episodes())
    assert [e["id"] for e in listed] == sorted([first, second], reverse=True)
    by_id = {e["id"]: e for e in listed}
    assert by_id[first]["end_reason"] == "exit" and by_id[first]["steps"] == dungeon.solution.length
    assert by_id[second]["end_reason"] == "stopped" and by_id[second]["running"] is False
    assert {"arch", "level", "seed", "optimal_steps", "started"} <= set(by_id[first])


def test_replay_gives_exactly_the_live_events(tmp_path: Path) -> None:  # SC-004
    dungeon = generate("L2", 1000)
    viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(replay_solution(dungeon)))
    episode_id = _start(viewer, level="L2")
    live = _events(viewer, episode_id)
    fresh = _viewer(tmp_path, OLLAMA)  # a restarted viewer has only the files
    replayed = fresh.session(episode_id)
    assert replayed is not None and replayed.done
    assert [event for _, event in (x for x in replayed.stream() if x)] == live


def test_saved_outcome_works_with_the_command_line_tools(tmp_path: Path) -> None:  # US4/AC3
    dungeon = generate("L2", 1001)
    viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(replay_solution(dungeon)))
    episode_id = _start(viewer, level="L2", seed=1001)
    _events(viewer, episode_id)
    outcome = json.loads((tmp_path / "viewer" / episode_id / "outcome.json").read_text())
    frames = parse_route_file(outcome).frames(dungeon)
    assert frames[-1].position == dungeon.layout.exit


@pytest.mark.parametrize(
    "episode_id", ["..", "../../etc", "20261030-120000-react-L1-1000/../x", "a/b", "nope", ""]
)
def test_bad_ids_never_touch_the_file_system(tmp_path: Path, episode_id: str) -> None:
    viewer = _viewer(tmp_path)
    assert viewer.session(episode_id) is None
    assert viewer.stop_episode(episode_id)[0] == 404
    assert not (tmp_path / "viewer").exists()


def test_error_episodes_are_saved_and_listed(tmp_path: Path) -> None:
    viewer = _viewer(
        tmp_path, OLLAMA, model_factory=scripted_factory(raise_error(FakeProviderError(401)))
    )
    episode_id = _start(viewer)
    _events(viewer, episode_id)
    (entry,) = _body(viewer.list_episodes())
    assert entry["id"] == episode_id and entry["end_reason"] == "error"


def test_the_viewer_plays_exactly_like_the_runner(tmp_path: Path) -> None:  # FR-007
    dungeon = generate("L2", 1002)
    viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(replay_solution(dungeon)))
    watched = _events(viewer, _start(viewer, level="L2", seed=1002))[-1]["data"]["row"]
    direct = play_episode(
        EpisodeKey("react", "L2", 1002, 1),
        "run",
        "dev",
        OLLAMA,
        ARCHS["react"],
        scripted_factory(replay_solution(dungeon)),
    ).row.to_dict()
    ignore = {"run_id", "latency_s"}
    assert {k: v for k, v in watched.items() if k not in ignore} == {
        k: v for k, v in direct.items() if k not in ignore
    }


def test_several_scouts_in_the_viewer(tmp_path: Path) -> None:  # specs/004 US3
    from apl.runner import registry
    from tests.arch.test_fanout import _strategy

    viewer = _viewer(
        tmp_path,
        OLLAMA,
        model_factory=scripted_factory(_strategy("L2", 1001)),
        architectures={"fanout": registry.load("fanout")},
    )
    episode_id = _start(viewer, "fanout", "L2", 1001)
    events = _events(viewer, episode_id)
    turns = {e["data"]["call"]: e["data"]["role"] for e in events if e["type"] == "turn"}
    steps = [e["data"] for e in events if e["type"] == "step"]
    assert turns[1] == "orchestrator" and {"scout 0", "scout 1", "scout 2"} <= set(turns.values())
    assert steps and all(s["scout"] == 0 for s in steps)  # only the walker moves
    assert all(turns[s["call"]] == "scout 0" for s in steps)
    assert all(len(s["frame"]["scouts"]) == 3 for s in steps)
    # The saved episode replays with every scout where it was.
    saved = json.loads((tmp_path / "viewer" / episode_id / "outcome.json").read_text())
    frames = parse_route_file(saved).frames(generate("L2", 1001))
    assert [f.position for f in frames[1:]] == [tuple(s["frame"]["position"]) for s in steps]
