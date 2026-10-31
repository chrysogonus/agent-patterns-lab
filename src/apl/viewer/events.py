"""Live episode events: the session that stores and streams them, and the model callbacks.

Research R2 (events), R3 (hooks), R5 (events.jsonl).
"""

import json
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from apl.dungeon.env import Episode
from apl.runner.meter import message_key

Event = dict[str, Any]


class EpisodeSession:
    """One episode's events, in order; appended only. Readers get the past, then follow live."""

    def __init__(self, episode_id: str, folder: Path) -> None:
        self.id = episode_id
        self.folder = folder
        self.events: list[Event] = []
        self.done = False
        self.call = 0  # the latest model call, so step events know their turn
        self.latest_call: dict[str, int] = {}  # the latest call of each role (specs/004 R6)
        self.episode: Episode | None = None  # set by on_episode; Stop needs it
        self.stop_requested = False
        self.thread: threading.Thread | None = None
        self._condition = threading.Condition()

    def emit(self, type: str, data: Any) -> None:
        event = {"type": type, "data": data}
        with self._condition:
            self.events.append(event)
            with (self.folder / "events.jsonl").open("a", encoding="utf-8") as file:
                file.write(json.dumps(event) + "\n")
            if type == "end":
                self.done = True
            self._condition.notify_all()

    def stream(self, start: int = 0, timeout: float = 15) -> Iterator[tuple[int, Event] | None]:
        """(index, event) pairs from `start` until the end; None after `timeout` s of quiet."""
        index = start
        while True:
            with self._condition:
                if index >= len(self.events) and not self.done:
                    self._condition.wait(timeout)
                batch, done = self.events[index:], self.done
            for event in batch:
                yield index, event
                index += 1
            if done and index >= len(self.events):
                return
            if not batch:
                yield None

    @classmethod
    def load(cls, folder: Path) -> "EpisodeSession":
        """A saved episode for replay. It counts as done even if it never got an `end`."""
        session = cls(folder.name, folder)
        lines = (folder / "events.jsonl").read_text(encoding="utf-8").splitlines()
        session.events = [json.loads(line) for line in lines if line.strip()]
        session.done = True
        return session


def _content(message: BaseMessage) -> str:
    text = str(message.text)
    if isinstance(message, AIMessage) and message.tool_calls:
        calls = ", ".join(f"{c['name']}({json.dumps(c['args'])})" for c in message.tool_calls)
        text = f"{text}\n→ {calls}" if text else f"→ {calls}"
    return text


class ViewerCallbacks(BaseCallbackHandler):
    """Turns model calls into `thinking` and `turn` events. Never breaks an episode."""

    raise_error = False

    def __init__(self, session: EpisodeSession) -> None:
        self.session = session
        self._previous: dict[str | None, list[str]] = {}  # by role
        # By run id: calls of several scouts can overlap (specs/004 research R6).
        self._started: dict[UUID, tuple[float, int, str | None]] = {}
        self._lock = threading.Lock()

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        # New input is what follows the prefix shared with the previous call. Deduplicating
        # against everything ever shown would hide A2's map whenever it did not change.
        role = (kwargs.get("metadata") or {}).get("role")
        keys = [message_key(m) for m in messages[0]]
        with self._lock:
            previous = self._previous.get(role, [])
            shared = 0
            while shared < min(len(keys), len(previous)) and keys[shared] == previous[shared]:
                shared += 1
            self._previous[role] = keys
            self.session.call += 1
            call = self.session.call
            if role is not None:
                self.session.latest_call[role] = call
            self._started[run_id] = (time.perf_counter(), call, role)
            new = [{"type": m.type, "content": _content(m)} for m in messages[0][shared:]]
            self.session.emit("thinking", {"call": call, "role": role, "new_input": new})

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        generation = response.generations[0][0]
        assert isinstance(generation, ChatGeneration)
        message = generation.message
        usage = getattr(message, "usage_metadata", None)
        meta = message.response_metadata
        with self._lock:
            started, call, role = self._started.pop(run_id, (time.perf_counter(), 0, None))
        self.session.emit(
            "turn",
            {
                "call": call or self.session.call,
                "role": role,
                "text": str(message.text),
                "reasoning": message.additional_kwargs.get("reasoning_content"),
                "tool_calls": [
                    {"name": c["name"], "args": c["args"]}
                    for c in getattr(message, "tool_calls", [])
                ],
                "invalid_tool_calls": [
                    {"name": c.get("name"), "args": c.get("args")}
                    for c in getattr(message, "invalid_tool_calls", [])
                ],
                "usage": (
                    {"input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"]}
                    if usage
                    else None
                ),
                "latency_s": round(time.perf_counter() - started, 3),
                "output_limit_hit": "length"
                in (meta.get("done_reason"), meta.get("finish_reason")),
            },
        )
