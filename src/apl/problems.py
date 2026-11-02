"""The problems the lab can run, by name (specs/005 contracts/problems.md, research R2).

Runner side only: architectures never import this module. LangChain is imported only when a kit
or a fingerprint is asked for, so `apl dungeon show` and `apl survey show` stay fast.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from apl import dungeon, rune, signal_trace, survey
from apl.dungeon.env import MAX_ATTEMPTS as DUNGEON_ATTEMPTS
from apl.rune.env import MAX_ATTEMPTS as RUNE_ATTEMPTS
from apl.signal_trace.env import MAX_ATTEMPTS as SIGNAL_ATTEMPTS
from apl.survey.env import MAX_ATTEMPTS as SURVEY_ATTEMPTS


@dataclass(frozen=True, slots=True)
class Problem:
    name: str
    levels: Mapping[str, Any]
    dev_seeds: range
    test_seeds: range
    generate: Callable[[str, int], Any]  # deterministic; the world has a `budget`
    reference_steps: Callable[[Any], int]  # the shortest solution, or the reference walk
    start_episode: Callable[[Any], Any]
    build_kit: Callable[[Any, Any], Any]  # (episode, model) -> Kit
    prompt_fingerprint: Callable[[], str]
    max_attempts: int  # for a retrying architecture (constitution 2.1.0, specs/007)

    @property
    def seed_sets(self) -> dict[str, range]:
        return {"dev": self.dev_seeds, "test": self.test_seeds}


def _dungeon_kit(episode: Any, model: Any) -> Any:
    from apl.kit import build_kit

    return build_kit(episode, model)


_dungeon_kit.__name__ = "build_kit"


def _dungeon_fingerprint() -> str:
    from apl.kit import prompt_fingerprint

    return prompt_fingerprint()


def _survey_kit(episode: Any, model: Any) -> Any:
    from apl.survey.kit import build_kit

    return build_kit(episode, model)


def _survey_fingerprint() -> str:
    from apl.survey.prompt import prompt_fingerprint

    return prompt_fingerprint()


def _signal_kit(episode: Any, model: Any) -> Any:
    from apl.signal_trace.kit import build_kit

    return build_kit(episode, model)


_signal_kit.__name__ = "build_kit"


def _signal_fingerprint() -> str:
    from apl.signal_trace.prompt import prompt_fingerprint

    return prompt_fingerprint()


def _rune_kit(episode: Any, model: Any) -> Any:
    from apl.rune.kit import build_kit

    return build_kit(episode, model)


_rune_kit.__name__ = "build_kit"


def _rune_fingerprint() -> str:
    from apl.rune.prompt import prompt_fingerprint

    return prompt_fingerprint()


PROBLEMS: dict[str, Problem] = {
    "dungeon": Problem(
        name="dungeon",
        levels=dungeon.LEVELS,
        dev_seeds=dungeon.DEV_SEEDS,
        test_seeds=dungeon.TEST_SEEDS,
        generate=dungeon.generate,
        reference_steps=lambda world: int(world.solution.length),
        start_episode=dungeon.start_episode,
        build_kit=_dungeon_kit,
        prompt_fingerprint=_dungeon_fingerprint,
        max_attempts=DUNGEON_ATTEMPTS,
    ),
    "survey": Problem(
        name="survey",
        levels=survey.LEVELS,
        dev_seeds=survey.DEV_SEEDS,
        test_seeds=survey.TEST_SEEDS,
        generate=survey.generate,
        reference_steps=lambda world: int(world.reference_steps),
        start_episode=survey.start_episode,
        build_kit=_survey_kit,
        prompt_fingerprint=_survey_fingerprint,
        max_attempts=SURVEY_ATTEMPTS,
    ),
    "signal": Problem(  # specs/009
        name="signal",
        levels=signal_trace.LEVELS,
        dev_seeds=signal_trace.DEV_SEEDS,
        test_seeds=signal_trace.TEST_SEEDS,
        generate=signal_trace.generate,
        reference_steps=lambda world: int(world.reference_steps),
        start_episode=signal_trace.start_episode,
        build_kit=_signal_kit,
        prompt_fingerprint=_signal_fingerprint,
        max_attempts=SIGNAL_ATTEMPTS,
    ),
    "rune": Problem(  # specs/010
        name="rune",
        levels=rune.LEVELS,
        dev_seeds=rune.DEV_SEEDS,
        test_seeds=rune.TEST_SEEDS,
        generate=rune.generate,
        reference_steps=lambda world: int(world.reference_steps),
        start_episode=rune.start_episode,
        build_kit=_rune_kit,
        prompt_fingerprint=_rune_fingerprint,
        max_attempts=RUNE_ATTEMPTS,
    ),
}
DEFAULT = "dungeon"


def get(name: str | None) -> Problem:
    """The named problem, or the dungeon for None; `ValueError` for an unknown name."""
    name = DEFAULT if name is None else name
    if name not in PROBLEMS:
        raise ValueError(f"unknown problem {name!r} (problems: {', '.join(PROBLEMS)})")
    return PROBLEMS[name]
