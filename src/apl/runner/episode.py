"""Plays one episode and sorts out how it ended (data-model "Episode flow", research R7, R8)."""

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import httpx
import openai
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel

from apl import problems
from apl.kit import EpisodeEnded, Kit
from apl.runner.meter import Meter, Transcript
from apl.runner.results import EpisodeRow
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey

ModelFactory = Callable[[Settings, list[BaseCallbackHandler]], BaseChatModel]

# The provider will refuse these the same way for every episode, so the run stops.
PERMANENT_STATUS = {400, 401, 403, 404, 422}


class PermanentProviderError(Exception):
    """The provider rejected a request in a way retrying cannot fix."""


@dataclass(frozen=True, slots=True)
class EpisodeResult:
    row: EpisodeRow
    # The Outcome of the episode's problem (apl.dungeon.env or apl.survey.env); None for an
    # infrastructure error.
    outcome: Any
    transcript: Transcript


def _describe(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def _is_provider_error(error: BaseException) -> bool:
    # httpx: a local server (Ollama) that is down or too slow; the OpenAI client wraps these itself.
    return isinstance(error, openai.APIError | httpx.TransportError) or isinstance(
        getattr(error, "status_code", None), int
    )


def _is_context_overflow(error: BaseException) -> bool:
    """The prompt no longer fits the model's context: the architecture's failure (R10)."""
    if getattr(error, "code", None) == "context_length_exceeded":
        return True
    return getattr(error, "status_code", None) == 400 and "maximum context length" in str(error)


def play_episode(
    key: EpisodeKey,
    run_id: str,
    seed_set: str,
    settings: Settings,
    play: Callable[[Kit], None],
    model_factory: ModelFactory,
    *,
    callbacks: Sequence[BaseCallbackHandler] = (),
    on_episode: Callable[[Any], None] | None = None,  # gets the problem's Episode
    problem: str = problems.DEFAULT,
) -> EpisodeResult:
    """Plays one episode. `callbacks` and `on_episode` let an observer (the viewer) watch it."""
    chosen = problems.get(problem)
    world = chosen.generate(key.level, key.seed)
    episode = chosen.start_episode(world)
    if on_episode is not None:
        on_episode(episode)
    meter = Meter(episode, settings.token_cap)
    if hasattr(episode, "turn_source"):  # the survey field counts parallel turns (specs/005 R11)
        episode.turn_source = lambda: meter.llm_calls
    kit = chosen.build_kit(episode, model_factory(settings, [meter, *callbacks]))
    arch_error = None
    started = time.perf_counter()
    try:
        play(kit)
    except EpisodeEnded:
        pass
    except Exception as error:
        if not _is_provider_error(error):
            arch_error = _describe(error)  # the architecture failed: scored as a failure
        elif _is_context_overflow(error):
            arch_error = "context window exceeded: " + _describe(error)
        elif getattr(error, "status_code", None) in PERMANENT_STATUS:
            raise PermanentProviderError(_describe(error)) from error
        else:  # retries are used up: an infrastructure error, not scored
            latency = time.perf_counter() - started
            row = EpisodeRow.failed(
                key, run_id, seed_set, episode, meter, latency, _describe(error),
                problem=chosen.name, optimal_steps=chosen.reference_steps(world),
                budget=world.budget,
            )  # fmt: skip
            return EpisodeResult(row, None, meter.transcript)
    episode.stop()  # the architecture returned early; does nothing if the episode already ended
    latency = time.perf_counter() - started
    outcome = episode.outcome()
    row = EpisodeRow.completed(
        key, run_id, seed_set, outcome, meter, latency, arch_error, problem=chosen.name
    )
    return EpisodeResult(row, outcome, meter.transcript)
