"""A scripted stand-in for the model, so tests never make a paid call (research R14)."""

import itertools
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler, CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable

from apl.dungeon.model import Action, Dungeon
from apl.runner.settings import Settings

Strategy = Callable[[list[BaseMessage]], AIMessage]
Usage = Callable[[list[BaseMessage]], UsageMetadata | None]

_ids = itertools.count(1)


def usage_per_call(input_tokens: int, output_tokens: int = 5) -> Usage:
    return lambda messages: UsageMetadata(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )


def default_usage(messages: list[BaseMessage]) -> UsageMetadata:
    return UsageMetadata(
        input_tokens=10 * len(messages), output_tokens=5, total_tokens=10 * len(messages) + 5
    )


class ScriptedChatModel(BaseChatModel):
    strategy: Strategy
    usage: Usage = default_usage

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        message = self.strategy(messages).model_copy(
            update={"usage_metadata": self.usage(messages)}
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable[Any, AIMessage]:
        return self.bind()


def scripted_factory(
    strategy: Strategy, usage: Usage = default_usage
) -> Callable[[Settings, list[BaseCallbackHandler]], BaseChatModel]:
    return lambda settings, callbacks: ScriptedChatModel(
        strategy=strategy, usage=usage, callbacks=callbacks
    )


def _args(action: Action) -> dict[str, str]:
    names = {"look": [], "move": ["direction"], "take": ["item"], "use": ["item", "direction"]}
    return dict(zip(names[action.tool], action.args, strict=True))


def tool_calls(*calls: tuple[str, Mapping[str, object]]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": n, "args": dict(a), "id": f"call_{next(_ids)}"} for n, a in calls],
    )


def _answered(messages: list[BaseMessage]) -> int:
    return sum(isinstance(m, ToolMessage) for m in messages)


def replay_solution(dungeon: Dungeon, per_turn: int = 1) -> Strategy:
    """The shortest solution as tool calls, `per_turn` calls per model turn."""
    actions = dungeon.solution.actions

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        done = _answered(messages)
        if done >= len(actions):
            return AIMessage("Done.")
        return tool_calls(*((a.tool, _args(a)) for a in actions[done : done + per_turn]))

    return strategy


def text_answer() -> Strategy:
    return lambda messages: AIMessage("I give up.")


def bump_wall(direction: str) -> Strategy:
    return lambda messages: tool_calls(("move", {"direction": direction}))


def unknown_tool() -> Strategy:
    return lambda messages: tool_calls(("open", {"door": "north"}))


def raise_error(error: BaseException) -> Strategy:
    def strategy(messages: list[BaseMessage]) -> AIMessage:
        raise error

    return strategy


def then(first: Strategy, calls: int, after: Strategy) -> Strategy:
    """`first` for the first `calls` model calls (counted across episodes), then `after`."""
    count = itertools.count()
    return lambda messages: (first if next(count) < calls else after)(messages)


class FakeProviderError(Exception):
    """Stands in for a provider error; the runner classifies by `status_code` (research R8)."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code
