"""Plays a run and writes its folder (contracts/results.md, research R8, R12)."""

import platform
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel

from apl.runner import registry
from apl.runner.episode import EpisodeResult, ModelFactory, PermanentProviderError, play_episode
from apl.runner.registry import Play
from apl.runner.results import RunRecord, append_row, write_json
from apl.runner.settings import Settings
from apl.runner.spec import RunSpec

_PACKAGES = ("langgraph", "langchain", "langchain-core", "langchain-openai")


def default_model_factory(
    settings: Settings, callbacks: list[BaseCallbackHandler]
) -> BaseChatModel:
    from langchain.chat_models import init_chat_model

    extra: dict[str, Any] = {}
    if settings.temperature is not None:
        extra["temperature"] = settings.temperature
    if settings.model.startswith("ollama:"):
        # The Ollama client has no retries; its timeout goes through client_kwargs.
        if settings.reasoning_effort is not None:
            effort = settings.reasoning_effort
            extra["reasoning"] = False if effort == "none" else effort
        model: BaseChatModel = init_chat_model(
            settings.model,
            callbacks=callbacks,
            num_ctx=settings.num_ctx,
            num_predict=settings.max_output_tokens,
            client_kwargs={"timeout": settings.timeout_s},
            **extra,
        )
        return model
    if settings.reasoning_effort is not None:
        extra["reasoning_effort"] = settings.reasoning_effort
    # The provider client retries rate limits, timeouts and 5xx with growing pauses (R8).
    model = init_chat_model(
        settings.model,
        callbacks=callbacks,
        max_retries=settings.max_retries,
        max_tokens=settings.max_output_tokens,
        timeout=settings.timeout_s,
        **extra,
    )
    return model


@dataclass(frozen=True, slots=True)
class RunOutcome:
    path: Path
    record: RunRecord
    exit_code: int  # 0, or 3 after a permanent provider rejection
    error: str | None


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _new_folder(results_dir: Path, architectures: Sequence[str], stamp: str) -> Path:
    """A new run folder; an existing one is never reused or overwritten."""
    base = f"{stamp}-{'+'.join(architectures)}"
    for n in range(1, 1000):
        path = results_dir / (base if n == 1 else f"{base}-{n}")
        try:
            path.mkdir(parents=True)
            return path
        except FileExistsError:
            continue
    raise RuntimeError(f"no free run folder name for {base}")


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _code_version() -> dict[str, Any]:
    commit, status = _git("rev-parse", "HEAD"), _git("status", "--porcelain")
    return {"commit": commit, "dirty": None if status is None else bool(status)}


def _versions() -> dict[str, str]:
    versions = {"python": platform.python_version()}
    for package in _PACKAGES:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            pass
    return versions


def execute(
    spec: RunSpec,
    settings: Settings,
    *,
    model_factory: ModelFactory | None = None,
    architectures: Mapping[str, Play] | None = None,
    results_dir: Path = Path("results"),
    on_episode: Callable[[int, int, EpisodeResult], None] | None = None,
) -> RunOutcome:
    """Plays every episode in order. A KeyboardInterrupt leaves run.json incomplete."""
    factory = model_factory or default_model_factory
    plays = {
        name: architectures[name] if architectures else registry.load(name)
        for name in spec.architectures
    }
    path = _new_folder(results_dir, spec.architectures, datetime.now().strftime("%Y%m%d-%H%M%S"))
    record = RunRecord(
        run_id=path.name,
        started=_now(),
        ended=None,
        completed=False,
        architectures=spec.architectures,
        levels=spec.levels,
        seed_set=spec.seed_set,
        seeds=spec.seeds,
        repeats=spec.repeats,
        settings=settings.record(),
        code=_code_version(),
        versions=_versions(),
    )
    write_json(path / "run.json", record.to_dict())
    episodes = path / "episodes"
    episodes.mkdir()
    keys = list(spec.episodes())
    for i, key in enumerate(keys, 1):
        try:
            result = play_episode(
                key, record.run_id, spec.seed_set, settings, plays[key.arch], factory
            )
        except PermanentProviderError as error:
            return RunOutcome(path, record, 3, str(error))
        if result.outcome is not None:
            write_json(episodes / f"{key.name}.outcome.json", result.outcome.to_dict())
        if result.row.llm_calls:
            write_json(episodes / f"{key.name}.conversation.json", result.transcript.to_dict())
        append_row(path / "episodes.jsonl", result.row)
        if on_episode is not None:
            on_episode(i, len(keys), result)
    record = replace(record, completed=True, ended=_now())
    write_json(path / "run.json", record.to_dict())
    return RunOutcome(path, record, 0, None)
