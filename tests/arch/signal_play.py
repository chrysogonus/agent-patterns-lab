"""Playing an architecture on the signal trace with a scripted model (specs/009 US1)."""

from collections.abc import Mapping

from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.signal_trace import generate
from apl.signal_trace.strategy import reference_run
from tests.runner.scripted import Strategy, play_calls, scripted_factory


def play(arch: str, level: str, seed: int, strategy: Strategy) -> EpisodeResult:
    key = EpisodeKey(arch, level, seed, 1)
    return play_episode(
        key, "test", "dev", Settings(), registry.load(arch), scripted_factory(strategy),
        problem="signal",
    )  # fmt: skip


def reference_calls(level: str, seed: int) -> list[tuple[str, Mapping[str, object]]]:
    probes, found = reference_run(generate(level, seed))
    return [*(("probe", {"segment": k}) for k, _ in probes), ("submit", {"segment": found})]


def reference(level: str, seed: int) -> Strategy:
    return play_calls(reference_calls(level, seed))
