"""Counts model calls and tokens, enforces the token cap and the end of the episode (research R3).

Attached through the model's own `callbacks` field: callbacks added with `with_config` are
dropped by `bind_tools`.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage, message_to_dict
from langchain_core.outputs import ChatGeneration, LLMResult

from apl.dungeon.env import Episode
from apl.kit import EpisodeEnded


def message_key(message: BaseMessage) -> str:
    """A message as sorted JSON: equal messages, equal keys (also used by the viewer)."""
    data = message_to_dict(message)
    flat = {"type": data["type"], **{k: v for k, v in data["data"].items() if k != "type"}}
    return json.dumps(flat, sort_keys=True, default=str)


@dataclass
class Transcript:
    """Each distinct message once; each call refers to its messages by index (research R12)."""

    messages: list[dict[str, Any]] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)
    _index: dict[str, int] = field(default_factory=dict)

    def add(self, message: BaseMessage) -> int:
        key = message_key(message)
        if key not in self._index:
            self._index[key] = len(self.messages)
            self.messages.append(json.loads(key))
        return self._index[key]

    def to_dict(self) -> dict[str, Any]:
        return {"messages": self.messages, "calls": self.calls}


class Meter(BaseCallbackHandler):
    raise_error = True  # so the guard's EpisodeEnded reaches the runner

    def __init__(self, episode: Episode, token_cap: int) -> None:
        self.episode = episode
        self.token_cap = token_cap
        self.llm_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.usage_missing = False
        self.token_cap_hit = False
        self.output_limit_hits = 0  # calls cut off by APL_MAX_OUTPUT_TOKENS
        self.transcript = Transcript()
        self._started: dict[UUID, tuple[float, list[int]]] = {}

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        if self.episode.end_reason is not None:
            raise EpisodeEnded
        self.llm_calls += 1
        inputs = [self.transcript.add(m) for m in messages[0]]
        self._started[run_id] = (time.perf_counter(), inputs)

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        started, inputs = self._started.pop(run_id)
        generation = response.generations[0][0]
        assert isinstance(generation, ChatGeneration)
        usage = getattr(generation.message, "usage_metadata", None)
        meta = generation.message.response_metadata  # Ollama: done_reason; OpenAI: finish_reason
        if "length" in (meta.get("done_reason"), meta.get("finish_reason")):
            self.output_limit_hits += 1
        self.transcript.calls.append(
            {
                "input": inputs,
                "output": self.transcript.add(generation.message),
                "usage": dict(usage) if usage else None,
                "latency_s": round(time.perf_counter() - started, 3),
            }
        )
        if usage is None:
            self.usage_missing = True
            return
        self.input_tokens += usage["input_tokens"]
        self.output_tokens += usage["output_tokens"]
        if self.input_tokens + self.output_tokens > self.token_cap and not self.token_cap_hit:
            self.token_cap_hit = True
            self.episode.stop()

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self._started.pop(run_id, None)
