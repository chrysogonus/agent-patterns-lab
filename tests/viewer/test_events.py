"""Event sessions and the viewer's model callbacks (research R2, R3)."""

import json
import threading
import uuid
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from apl.dungeon import generate
from apl.runner.episode import play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.viewer.events import EpisodeSession, ViewerCallbacks
from tests.runner import loop_arch
from tests.runner.scripted import replay_solution, scripted_factory


def _session(tmp_path: Path) -> EpisodeSession:
    folder = tmp_path / "s"
    folder.mkdir()
    return EpisodeSession("s", folder)


def test_late_readers_get_everything_then_follow(tmp_path: Path) -> None:
    session = _session(tmp_path)
    session.emit("start", {"n": 0})
    session.emit("step", {"n": 1})
    seen: list[int] = []

    def read() -> None:
        for item in session.stream():
            if item is not None:
                seen.append(item[0])

    reader = threading.Thread(target=read)
    reader.start()
    session.emit("step", {"n": 2})
    session.emit("end", {"n": 3})
    reader.join(timeout=5)
    assert seen == [0, 1, 2, 3] and session.done
    assert [i for i, _ in (x for x in session.stream(2) if x)] == [2, 3]  # resume after an id
    lines = (session.folder / "events.jsonl").read_text().splitlines()
    assert [json.loads(line) for line in lines] == session.events


def test_idle_stream_yields_keepalives(tmp_path: Path) -> None:
    session = _session(tmp_path)
    stream = session.stream(timeout=0.01)
    assert next(stream) is None  # nothing happened: the server sends a keepalive comment


def _start(callbacks: ViewerCallbacks, messages: list[BaseMessage]) -> uuid.UUID:
    run_id = uuid.uuid4()
    callbacks.on_chat_model_start({}, [messages], run_id=run_id)
    return run_id


def test_new_input_is_what_follows_the_shared_prefix(tmp_path: Path) -> None:
    session = _session(tmp_path)
    callbacks = ViewerCallbacks(session)
    system, start = SystemMessage("rules"), HumanMessage("start")
    reply = AIMessage("", tool_calls=[{"name": "look", "args": {}, "id": "c1"}])
    result = ToolMessage('{"ok": true}', tool_call_id="c1")
    a1 = [system, start]
    _start(callbacks, a1)
    _start(callbacks, [*a1, reply, result])  # A1: the history grows
    map_text = HumanMessage("Your map: c3")
    _start(callbacks, [system, reply, result, map_text])  # A2: only the system message is shared
    again = AIMessage("", tool_calls=[{"name": "look", "args": {}, "id": "c2"}])
    result2 = ToolMessage('{"ok": true}', tool_call_id="c2")
    _start(callbacks, [system, again, result2, map_text])  # an unchanged map shows up again
    thinking = [e["data"] for e in session.events if e["type"] == "thinking"]
    assert [t["call"] for t in thinking] == [1, 2, 3, 4]
    assert [m["type"] for m in thinking[0]["new_input"]] == ["system", "human"]
    assert [m["type"] for m in thinking[1]["new_input"]] == ["ai", "tool"]
    assert "look" in thinking[1]["new_input"][0]["content"]  # a tool-call reply is not blank
    assert [m["content"] for m in thinking[3]["new_input"]][-1] == "Your map: c3"
    assert len(thinking[2]["new_input"]) == len(thinking[3]["new_input"]) == 3


def test_turn_event(tmp_path: Path) -> None:
    session = _session(tmp_path)
    callbacks = ViewerCallbacks(session)
    run_id = _start(callbacks, [HumanMessage("start")])
    reply = AIMessage(
        "Going north.",
        tool_calls=[{"name": "move", "args": {"direction": "north"}, "id": "c1"}],
        additional_kwargs={"reasoning_content": "North looks open."},
        usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        response_metadata={"finish_reason": "length"},
    )
    callbacks.on_llm_end(LLMResult(generations=[[ChatGeneration(message=reply)]]), run_id=run_id)
    turn = session.events[-1]
    assert turn["type"] == "turn"
    data = turn["data"]
    assert data["call"] == 1 and data["text"] == "Going north."
    assert data["reasoning"] == "North looks open."
    assert data["tool_calls"] == [{"name": "move", "args": {"direction": "north"}}]
    assert data["invalid_tool_calls"] == []
    assert data["usage"] == {"input_tokens": 100, "output_tokens": 20}
    assert data["latency_s"] >= 0 and data["output_limit_hit"] is True


def test_a_broken_viewer_never_ends_an_episode(tmp_path: Path) -> None:
    session = _session(tmp_path)

    def broken(type: str, data: object) -> None:
        raise OSError("disk full")

    session.emit = broken  # type: ignore[method-assign]
    result = play_episode(
        EpisodeKey("loop", "L1", 1000, 1),
        "test",
        "dev",
        Settings(),
        loop_arch.play,
        scripted_factory(replay_solution(generate("L1", 1000))),
        callbacks=[ViewerCallbacks(session)],
    )
    assert result.row.success and result.row.arch_error is None
