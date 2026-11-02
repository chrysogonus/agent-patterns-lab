"""Playing an architecture on the rune floor with a scripted model (specs/010 US1)."""

from collections.abc import Callable, Mapping

from apl.rune import Episode, generate
from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from tests.rune.agents import reference_moves
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
        on_episode=on_episode, problem="rune",
    )  # fmt: skip


def reference_calls(level: str, seed: int) -> list[tuple[str, Mapping[str, object]]]:
    return [("move", {"direction": d}) for d in reference_moves(generate(level, seed))]


def reference(level: str, seed: int) -> Strategy:
    return play_calls(reference_calls(level, seed))
