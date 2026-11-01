"""A scripted stand-in for the model, so tests never make a paid call (research R14)."""

import itertools
import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler, CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable

from apl.dungeon.env import start_episode
from apl.dungeon.frames import call
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


def replay_solution(dungeon: Dungeon, per_turn: int = 1) -> Strategy:
    """The shortest solution as tool calls, `per_turn` calls per model turn."""
    actions = dungeon.solution.actions
    calls = itertools.count()  # counts its own calls: A2 does not send the history (R17)

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        done = next(calls) * per_turn
        if done >= len(actions):
            return AIMessage("Done.")
        return tool_calls(*((a.tool, _args(a)) for a in actions[done : done + per_turn]))

    return strategy


_HERE = re.compile(r"You are in: (\S+)\. Inventory: (.*)\.")


def _state(text: str) -> tuple[str, str, int] | None:
    """(room, inventory, doors opened) from a rendered map's text."""
    here = _HERE.search(text)
    if here is None:
        return None
    opened = re.search(r"Doors you opened: (.*)\.", text)
    return here[1], here[2], len(opened[1].split("; ")) if opened else 0


def next_action(dungeon: Dungeon) -> Callable[[list[BaseMessage]], Action | None]:
    """The solution's next action from the state the last message's map shows, if on its path."""
    episode = start_episode(dungeon)
    states: dict[tuple[str, str, int], Action] = {}
    for action in dungeon.solution.actions:
        room = episode.describe()
        states[room.label, ", ".join(room.inventory) or "nothing", len(episode.opened)] = action
        call(episode, action)

    def find(messages: list[BaseMessage]) -> Action | None:
        state = _state(str(messages[-1].content))
        return states.get(state) if state else None

    return find


def walk_solution(dungeon: Dungeon) -> Strategy:
    """For map-showing agents: the solution's next action from the state the last map shows.

    It reads no counter, so parallel scouts get the same answer in any order. Off the solution's
    path it answers with text, which ends a scout's task.
    """
    find = next_action(dungeon)

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        action = find(messages)
        if action is None:
            return AIMessage("Nothing to do here.")
        return tool_calls((action.tool, _args(action)))

    return strategy


def by_system(routes: Mapping[str, Strategy], default: Strategy) -> Strategy:
    """The strategy of the first marker found in the system message (orchestrator or scout)."""

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        system = str(messages[0].content)
        found = next((s for marker, s in routes.items() if marker in system), default)
        return found(messages)

    return strategy


def by_task(routes: Mapping[str, Strategy], default: Strategy) -> Strategy:
    """The strategy whose key is in the scout's task line."""

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        text = "\n".join(str(m.content) for m in messages)
        task = text.split("Your task: ", 1)[1].split("\n", 1)[0] if "Your task: " in text else ""
        return next((s for key, s in routes.items() if key in task), default)(messages)

    return strategy


def json_answer(answer: object) -> Strategy:
    return lambda messages: AIMessage(json.dumps(answer))


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

    def __init__(self, status_code: int, message: str = "", code: str | None = None) -> None:
        super().__init__(f"HTTP {status_code}" + (f": {message}" if message else ""))
        self.status_code = status_code
        self.code = code


_CELL = re.compile(r'You are in: (\w+)\.|"cell": "(\w+)"')  # a map, or a raw tool result


def walk_field(walk: Sequence[str], start: str = "A1", total: int | None = None) -> Strategy:
    """Survey field (specs/005): the reference walk's next move from the cell the last message
    shows (a map's "You are in", or a tool result's "cell").

    At the walk's end it submits `total`, or answers with a report. It reads no counter, so
    parallel scouts get the same answer in any order.
    """
    from apl.survey.model import STEP, cell_name

    def pos(name: str) -> tuple[int, int]:
        return "ABCDEFGHIJ".index(name[0]), int(name[1:]) - 1

    nexts, here = {}, pos(start)
    for direction in walk:
        nexts[cell_name(here)] = direction
        here = (here[0] + STEP[direction][0], here[1] + STEP[direction][1])
    end = cell_name(here)

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        found = _CELL.search(str(messages[-1].content))
        cell = (found[1] or found[2]) if found else None
        if cell in nexts:
            return tool_calls(("move", {"direction": nexts[cell]}))
        if cell == end and total is not None:
            return tool_calls(("submit", {"total": total}))
        return AIMessage("I walked my part of the field.")

    return strategy
