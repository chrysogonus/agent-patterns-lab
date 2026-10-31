"""Helpers for the A7–A9 tests: play an episode and keep every model input with its role."""

from langchain_core.messages import AIMessage, BaseMessage

from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from tests.runner.scripted import Strategy, scripted_factory


def play(arch: str, level: str, seed: int, strategy: Strategy) -> EpisodeResult:
    key = EpisodeKey(arch, level, seed, 1)
    return play_episode(
        key, "test", "dev", Settings(), registry.load(arch), scripted_factory(strategy)
    )


def recording(inner: Strategy, seen: list[list[BaseMessage]]) -> Strategy:
    def strategy(messages: list[BaseMessage]) -> AIMessage:
        seen.append(list(messages))
        return inner(messages)

    return strategy


def roles(result: EpisodeResult) -> list[str | None]:
    return [call.get("role") for call in result.transcript.calls]


def text(messages: list[BaseMessage]) -> str:
    return "\n".join(str(m.content) for m in messages)
