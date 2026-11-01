"""Plays a run and writes its folder (contracts/results.md, research R8, R12)."""

import json
import platform
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import httpx
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.utils import convert_to_secret_str

from apl.runner import registry
from apl.runner.episode import EpisodeResult, ModelFactory, PermanentProviderError, play_episode
from apl.runner.registry import Play
from apl.runner.results import EpisodeRow, RunRecord, append_row, write_json
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey, RunSpec

_PACKAGES = (
    "langgraph",
    "langchain",
    "langchain-core",
    "langchain-openai",
    "langchain-ollama",
    "ollama",
)
_TRANSIENT_STATUS = {429, 500, 502, 503, 504}


class RetryTransport(httpx.BaseTransport):
    """Retries rate limits, 5xx and connection errors with growing pauses (FR-017).

    For Ollama, whose client does not retry. shortcut: a read timeout while a streamed answer is
    arriving is not retried (it becomes an infrastructure error); fine for a local server.
    """

    def __init__(
        self, retries: int, inner: httpx.BaseTransport | None = None, pause: float = 0.5
    ) -> None:
        self.retries = retries
        self.inner = inner or httpx.HTTPTransport()
        self.pause = pause

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        for attempt in range(self.retries + 1):
            last = attempt == self.retries
            try:
                response = self.inner.handle_request(request)
            except httpx.TransportError:
                if last:
                    raise
            else:
                if last or response.status_code not in _TRANSIENT_STATUS:
                    return response
                response.close()
            time.sleep(self.pause * 2**attempt)
        raise AssertionError("unreachable")

    def close(self) -> None:
        self.inner.close()


def default_model_factory(
    settings: Settings, callbacks: list[BaseCallbackHandler]
) -> BaseChatModel:
    from langchain.chat_models import init_chat_model

    extra: dict[str, Any] = {}
    if settings.temperature is not None:
        extra["temperature"] = settings.temperature
    if settings.model.startswith("vllm:"):
        from apl.runner.vllm import VLLMChat

        if settings.reasoning_effort is not None:
            extra["reasoning_effort"] = settings.reasoning_effort
        return VLLMChat(
            model=settings.model.removeprefix("vllm:"),
            base_url=settings.base_url,
            api_key=convert_to_secret_str("EMPTY"),  # vLLM needs no key
            callbacks=callbacks,
            max_retries=settings.max_retries,
            max_tokens=settings.max_output_tokens,  # type: ignore[call-arg]
            timeout=settings.timeout_s,
            **extra,
        )
    if settings.model.startswith("ollama:"):
        # The Ollama client has no retries of its own and takes its timeout through client_kwargs.
        if settings.reasoning_effort is not None:
            effort = settings.reasoning_effort
            extra["reasoning"] = False if effort == "none" else effort
        model: BaseChatModel = init_chat_model(
            settings.model,
            callbacks=callbacks,
            num_ctx=settings.num_ctx,
            num_predict=settings.max_output_tokens,
            client_kwargs={"timeout": settings.timeout_s},
            sync_client_kwargs={"transport": RetryTransport(settings.max_retries)},
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
    exit_code: int  # 0; 3 after a permanent provider rejection; 4 after 3 errors in a row; 130
    error: str | None


ERRORS_IN_A_ROW = 3  # infrastructure errors that stop a run (specs/004 research R13)


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


def code_version() -> dict[str, Any]:
    commit, status = _git("rev-parse", "HEAD"), _git("status", "--porcelain")
    return {"commit": commit, "dirty": None if status is None else bool(status)}


def package_versions() -> dict[str, str]:
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
        settings=settings.record(spec.problem),
        code=code_version(),
        versions=package_versions(),
        problem=spec.problem,
    )
    write_json(path / "run.json", record.to_dict())
    (path / "episodes").mkdir()
    keys = list(spec.episodes())
    return _play(path, record, keys, 0, len(keys), settings, plays, factory, on_episode)


def _play(
    path: Path,
    record: RunRecord,
    keys: Sequence[EpisodeKey],
    done: int,
    total: int,
    settings: Settings,
    plays: Mapping[str, Play],
    factory: ModelFactory,
    on_episode: Callable[[int, int, EpisodeResult], None] | None,
) -> RunOutcome:
    """Plays `keys` into the run folder; numbers them after the `done` ones."""
    episodes = path / "episodes"
    errors = 0
    for i, key in enumerate(keys, done + 1):
        try:
            result = play_episode(
                key,
                record.run_id,
                record.seed_set,
                settings,
                plays[key.arch],
                factory,
                problem=record.problem,
            )
        except PermanentProviderError as error:
            return RunOutcome(path, record, 3, str(error))
        except KeyboardInterrupt:
            return RunOutcome(path, record, 130, "interrupted")
        if result.outcome is not None:
            write_json(episodes / f"{key.name}.outcome.json", result.outcome.to_dict())
        if result.row.llm_calls:
            write_json(episodes / f"{key.name}.conversation.json", result.transcript.to_dict())
        append_row(path / "episodes.jsonl", result.row)
        if on_episode is not None:
            on_episode(i, total, result)
        errors = errors + 1 if result.row.status == "error" else 0
        if errors >= ERRORS_IN_A_ROW:
            message = f"the provider failed {ERRORS_IN_A_ROW} episodes in a row; run stopped"
            return RunOutcome(path, record, 4, message)
    record = replace(record, completed=True, ended=_now())
    write_json(path / "run.json", record.to_dict())
    return RunOutcome(path, record, 0, None)


@dataclass(frozen=True, slots=True)
class ContinuePlan:
    """What continuing a run would do; nothing is changed until `continue_run` (research R11)."""

    path: Path
    record: RunRecord
    done: frozenset[EpisodeKey]
    left: tuple[EpisodeKey, ...]
    cut_off: bool  # the last row was cut off by a hard stop
    refusals: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """Marked complete. With no episode left but no mark, continuing only marks it."""
        return self.record.completed


def plan_continue(
    path: Path,
    settings: Settings,
    *,
    code: Mapping[str, Any],
    versions: Mapping[str, str],
    written: Mapping[str, bool],
) -> ContinuePlan:
    """Reads a run folder without changing it; `ValueError` if it is not a readable run."""
    run_json = path / "run.json"
    if not run_json.is_file():
        raise ValueError(f"{path} is not a run folder (no run.json)")
    try:
        record = RunRecord.parse(json.loads(run_json.read_text(encoding="utf-8")))
    except ValueError as error:  # includes JSONDecodeError
        raise ValueError(f"{run_json}: {error}") from None
    rows_path = path / "episodes.jsonl"
    text = rows_path.read_text(encoding="utf-8") if rows_path.exists() else ""
    lines = text.splitlines()
    cut_off = bool(text) and not text.endswith("\n")  # a row is written with its newline
    done = set()
    for number, line in enumerate(lines[:-1] if cut_off else lines, 1):
        try:
            row = EpisodeRow.parse(json.loads(line))
        except ValueError as error:
            raise ValueError(f"{rows_path}:{number}: {error}") from None
        done.add(EpisodeKey(row.arch, row.level, row.seed, row.repeat))
    spec = RunSpec(
        record.architectures,
        record.levels,
        record.seed_set,
        record.seeds,
        record.repeats,
        record.problem,
    )
    left = tuple(k for k in spec.episodes() if k not in done)
    refusals = []
    now = settings.record(record.problem)
    for name in sorted(record.settings.keys() | now.keys()):
        if record.settings.get(name) != now.get(name):
            refusals.append(
                f"setting {name} differs (run: {record.settings.get(name)}, now: {now.get(name)})"
            )
    for name in sorted(record.versions.keys() | versions.keys()):
        if record.versions.get(name) != versions.get(name):
            refusals.append(
                f"version of {name} differs "
                f"(run: {record.versions.get(name)}, now: {versions.get(name)})"
            )
    if record.code.get("commit") != code.get("commit"):
        refusals.append(
            f"commit differs (run: {record.code.get('commit')}, now: {code.get('commit')})"
        )
    if code.get("dirty") is not False:
        refusals.append("the working tree has uncommitted changes; commit or stash them")
    if record.code.get("dirty") is not False:
        refusals.append("the run was started with uncommitted changes; it cannot be continued")
    for name in record.architectures:
        if name not in written:
            refusals.append(f"unknown architecture {name!r}")
        elif not written[name]:
            refusals.append(f"architecture {name} is not written yet")
    return ContinuePlan(path, record, frozenset(done), left, cut_off, tuple(refusals))


def continue_run(
    plan: ContinuePlan,
    settings: Settings,
    *,
    model_factory: ModelFactory | None = None,
    architectures: Mapping[str, Play] | None = None,
    on_episode: Callable[[int, int, EpisodeResult], None] | None = None,
) -> RunOutcome:
    """Plays the missing episodes of a plan without refusals into the same folder."""
    if plan.refusals:
        raise ValueError("cannot continue: " + "; ".join(plan.refusals))
    plays = {
        name: architectures[name] if architectures else registry.load(name)
        for name in plan.record.architectures
    }
    if plan.cut_off:
        rows = plan.path / "episodes.jsonl"
        text = rows.read_text(encoding="utf-8")
        rows.write_text(text[: text.rfind("\n") + 1], encoding="utf-8")
    (plan.path / "episodes").mkdir(exist_ok=True)
    total = len(plan.done) + len(plan.left)
    factory = model_factory or default_model_factory
    return _play(
        plan.path,
        plan.record,
        plan.left,
        len(plan.done),
        total,
        settings,
        plays,
        factory,
        on_episode,
    )
