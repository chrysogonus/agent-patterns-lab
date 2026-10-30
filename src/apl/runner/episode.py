"""Plays one episode and sorts out how it ended (data-model "Episode flow", research R7, R8)."""

import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx
import openai
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel

from apl.dungeon import generate, start_episode
from apl.dungeon.env import Outcome
from apl.kit import EpisodeEnded, Kit, build_kit
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
    outcome: Outcome | None  # None for an infrastructure error
    transcript: Transcript


def _describe(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def _is_provider_error(error: BaseException) -> bool:
    # httpx: a local server (Ollama) that is down or too slow; the OpenAI client wraps these itself.
    return isinstance(error, openai.APIError | httpx.TransportError) or isinstance(
        getattr(error, "status_code", None), int
    )


def play_episode(
    key: EpisodeKey,
    run_id: str,
    seed_set: str,
    settings: Settings,
    play: Callable[[Kit], None],
    model_factory: ModelFactory,
) -> EpisodeResult:
    episode = start_episode(generate(key.level, key.seed))
    meter = Meter(episode, settings.token_cap)
    kit = build_kit(episode, model_factory(settings, [meter]))
    arch_error = None
    started = time.perf_counter()
    try:
        play(kit)
    except EpisodeEnded:
        pass
    except Exception as error:
        if not _is_provider_error(error):
            arch_error = _describe(error)  # the architecture failed: scored as a failure
        elif getattr(error, "status_code", None) in PERMANENT_STATUS:
            raise PermanentProviderError(_describe(error)) from error
        else:  # retries are used up: an infrastructure error, not scored
            latency = time.perf_counter() - started
            row = EpisodeRow.failed(
                key, run_id, seed_set, episode, meter, latency, _describe(error)
            )
            return EpisodeResult(row, None, meter.transcript)
    episode.stop()  # the architecture returned early; does nothing if the episode already ended
    latency = time.perf_counter() - started
    outcome = episode.outcome()
    row = EpisodeRow.completed(key, run_id, seed_set, outcome, meter, latency, arch_error)
    return EpisodeResult(row, outcome, meter.transcript)
