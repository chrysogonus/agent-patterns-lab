"""Playing an architecture on the workshop with a scripted model (specs/011 US1)."""

from collections.abc import Callable

from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.workshop import Episode, generate
from apl.workshop.plans import greedy_calls, reference_calls
from tests.runner.scripted import Strategy, play_calls, scripted_factory


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
        on_episode=on_episode, problem="workshop",
    )  # fmt: skip


def reference(level: str, seed: int) -> Strategy:
    return play_calls(reference_calls(generate(level, seed)))


def greedy(level: str, seed: int) -> Strategy:
    return play_calls(greedy_calls(generate(level, seed)))
