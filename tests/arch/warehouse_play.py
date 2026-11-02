"""Playing an architecture on the warehouse with a scripted model (specs/012 US1)."""

import re
from collections.abc import Callable

from langchain_core.messages import AIMessage, BaseMessage

from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.warehouse import Episode, generate
from apl.warehouse.model import Action
from apl.warehouse.plans import as_calls
from tests.runner.scripted import Strategy, play_calls, scripted_factory, tool_calls


def play(
    arch: str,
    level: str,
    seed: int,
    strategy: Strategy,
    on_episode: Callable[[Episode], None] | None = None,
) -> EpisodeResult:
    key = EpisodeKey(arch, level, seed, 1)
    return play_episode(
        key, "test", "dev", Settings(), registry.load(arch), scripted_factory(strategy),
        on_episode=on_episode, problem="warehouse",
    )  # fmt: skip


def reference(level: str, seed: int) -> Strategy:
    return play_calls(as_calls(generate(level, seed).reference))


def robot_actions(episode: Episode) -> dict[int, list[Action]]:
    """Each robot's calls in a played episode, in order (for scripted robots)."""
    found: dict[int, list[Action]] = {}
    for entry in episode.log:
        if entry.step is not None:
            found.setdefault(entry.scout, []).append(entry.action)
    return found


def robots(actions: dict[int, list[Action]]) -> Strategy:
    """Scripted robots: robot n (from its task line) replays its own calls, then reports."""
    queues = {n: iter(as_calls(a)) for n, a in actions.items()}

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        found = re.search(r"You are robot (\d+)\.", "\n".join(str(m.content) for m in messages))
        number = int(found[1]) if found else 0
        call = next(queues.get(number, iter(())), None)
        return tool_calls(call) if call else AIMessage("Done.")

    return strategy
