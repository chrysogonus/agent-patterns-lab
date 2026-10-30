"""Playing runs end to end with the scripted model (User Story 2, research R7, R8, R12)."""

import json
import time
from pathlib import Path

import httpx
import pytest

from apl.dungeon import DEV_SEEDS, generate
from apl.dungeon.frames import parse_route_file
from apl.dungeon.model import Direction
from apl.runner.results import EpisodeRow, RunRecord
from apl.runner.run import RetryTransport, RunOutcome, _new_folder, default_model_factory, execute
from apl.runner.settings import Settings
from apl.runner.spec import RunSpec
from tests.runner import loop_arch
from tests.runner.scripted import (
    FakeProviderError,
    Strategy,
    Usage,
    bump_wall,
    default_usage,
    raise_error,
    replay_solution,
    scripted_factory,
    text_answer,
    then,
    usage_per_call,
)

ARCHS = {"loop": loop_arch.play, "crash": loop_arch.crash}


def _run(
    tmp_path: Path,
    strategy: Strategy,
    *,
    arch: str = "loop",
    levels: tuple[str, ...] = ("L1",),
    only: tuple[int, ...] = (1000,),
    usage: Usage = default_usage,
    settings: Settings | None = None,
) -> RunOutcome:
    spec = RunSpec.build([arch], list(levels), "dev", only=list(only), known=ARCHS)
    return execute(
        spec,
        settings or Settings(),
        model_factory=scripted_factory(strategy, usage),
        architectures=ARCHS,
        results_dir=tmp_path,
    )


def _rows(outcome: RunOutcome) -> list[EpisodeRow]:
    lines = (outcome.path / "episodes.jsonl").read_text().splitlines()
    return [EpisodeRow.parse(json.loads(line)) for line in lines]


def _record(outcome: RunOutcome) -> RunRecord:
    return RunRecord.parse(json.loads((outcome.path / "run.json").read_text()))


def _wall(level: str = "L1", seed: int = 1000) -> str:
    """A direction from the start room with no door, so moving there always fails."""
    layout = generate(level, seed).layout
    return next(str(d) for d in Direction if layout.door(layout.start, d) is None)


@pytest.mark.parametrize("seed", DEV_SEEDS)
@pytest.mark.parametrize("level", ["L1", "L2", "L3"])
def test_perfect_replay(tmp_path: Path, level: str, seed: int) -> None:  # SC-002
    dungeon = generate(level, seed)
    outcome = _run(tmp_path, replay_solution(dungeon), levels=(level,), only=(seed,))
    (row,) = _rows(outcome)
    assert row.status == "completed" and row.success and row.efficiency == 1.0
    assert row.steps == row.optimal_steps == dungeon.solution.length
    assert row.invalid_actions == 0
    assert row.llm_calls == row.steps  # the exit ends the episode inside the tool node
    calls = json.loads(
        (outcome.path / "episodes" / f"loop-{level}-{seed}-r1.conversation.json").read_text()
    )["calls"]
    assert row.input_tokens == sum(c["usage"]["input_tokens"] for c in calls)
    assert row.output_tokens == 5 * row.llm_calls


def test_text_answer_stops(tmp_path: Path) -> None:
    (row,) = _rows(_run(tmp_path, text_answer()))
    assert row.end_reason == "stopped" and row.steps == 0 and row.success is False
    assert row.llm_calls == 1 and row.arch_error is None


def test_budget_ends_without_another_call(tmp_path: Path) -> None:
    (row,) = _rows(_run(tmp_path, bump_wall(_wall())))
    assert row.invalid_actions == row.steps
    assert row.budget_hit and row.end_reason == "budget"
    assert row.llm_calls == row.budget == row.steps


def test_token_cap_ends_without_another_call(tmp_path: Path) -> None:
    (row,) = _rows(_run(tmp_path, bump_wall(_wall()), usage=usage_per_call(400_000)))
    assert row.token_cap_hit and row.end_reason == "stopped" and row.llm_calls == 2
    assert row.steps == 1  # the second call's tool calls were not carried out


def test_crash_counts_as_failure(tmp_path: Path) -> None:
    (row,) = _rows(_run(tmp_path, text_answer(), arch="crash"))
    assert row.status == "completed" and row.success is False
    assert row.end_reason == "stopped" and row.arch_error == "ValueError: boom"


def test_transient_provider_error_is_not_scored(tmp_path: Path) -> None:
    strategy = then(text_answer(), 1, raise_error(FakeProviderError(429)))
    outcome = _run(tmp_path, strategy, only=(1000, 1001))
    first, second = _rows(outcome)
    assert first.status == "completed"
    assert second.status == "error" and second.error == "FakeProviderError: HTTP 429"
    assert second.success is None and second.optimal_steps > 0
    assert outcome.exit_code == 0 and _record(outcome).completed
    assert not (outcome.path / "episodes" / "loop-L1-1001-r1.outcome.json").exists()


def test_permanent_provider_error_stops_the_run(tmp_path: Path) -> None:
    strategy = then(text_answer(), 1, raise_error(FakeProviderError(401)))
    outcome = _run(tmp_path, strategy, only=(1000, 1001, 1002))
    assert outcome.exit_code == 3 and "HTTP 401" in str(outcome.error)
    assert len(_rows(outcome)) == 1
    record = _record(outcome)
    assert not record.completed and record.ended is None


def test_interrupt_keeps_finished_rows(tmp_path: Path) -> None:
    strategy = then(text_answer(), 1, raise_error(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        _run(tmp_path, strategy, only=(1000, 1001))
    (run,) = tmp_path.iterdir()
    assert len((run / "episodes.jsonl").read_text().splitlines()) == 1
    assert json.loads((run / "run.json").read_text())["completed"] is False


def test_saved_logs_replay(tmp_path: Path) -> None:
    outcome = _run(tmp_path, bump_wall(_wall()), only=(1000, 1001))
    for row in _rows(outcome):
        name = f"loop-L1-{row.seed}-r1"
        record = json.loads((outcome.path / "episodes" / f"{name}.outcome.json").read_text())
        frames = parse_route_file(record).frames(generate("L1", row.seed))
        assert frames[-1].step == row.steps and frames[-1].end_reason == row.end_reason
        conversation = json.loads(
            (outcome.path / "episodes" / f"{name}.conversation.json").read_text()
        )
        assert len(conversation["calls"]) == row.llm_calls


def test_run_record(tmp_path: Path) -> None:
    record = _record(_run(tmp_path, text_answer()))
    assert record.completed and record.ended is not None
    assert record.architectures == ("loop",) and record.seeds == (1000,)
    assert record.seed_set == "dev" and record.repeats == 1
    assert record.settings == Settings().record()
    assert set(record.code) == {"commit", "dirty"}
    assert {
        "python",
        "langgraph",
        "langchain",
        "langchain-core",
        "langchain-openai",
        "langchain-ollama",
        "ollama",
    } <= set(record.versions)
    assert "OPENAI_API_KEY" not in (tmp_path / record.run_id / "run.json").read_text()


def test_new_folders_never_clash(tmp_path: Path) -> None:
    first = _new_folder(tmp_path, ("loop",), "20261030-151200")
    second = _new_folder(tmp_path, ("loop", "crash"), "20261030-151200")
    third = _new_folder(tmp_path, ("loop",), "20261030-151200")
    assert [first.name, second.name, third.name] == [
        "20261030-151200-loop",
        "20261030-151200-loop+crash",
        "20261030-151200-loop-2",
    ]


def test_runner_overhead_is_small(tmp_path: Path) -> None:
    spec = RunSpec.build(["loop"], ["L1"], "dev", known=ARCHS)
    replays = {s: replay_solution(generate("L1", s)) for s in spec.seeds}
    current = iter(spec.seeds)
    seed = [next(current)]

    def strategy(messages: list) -> object:  # type: ignore[type-arg]
        return replays[seed[0]](messages)

    def advance(i: int, n: int, result: object) -> None:
        seed[0] = next(current, seed[0])

    started = time.perf_counter()
    execute(
        spec,
        Settings(),
        model_factory=scripted_factory(strategy),  # type: ignore[arg-type]
        architectures=ARCHS,
        results_dir=tmp_path,
        on_episode=advance,
    )
    assert (time.perf_counter() - started) / len(spec.seeds) < 1.0  # SC-010


def test_local_server_down_is_not_scored(tmp_path: Path) -> None:
    (row,) = _rows(_run(tmp_path, raise_error(httpx.ConnectError("connection refused"))))
    assert row.status == "error" and row.error == "ConnectError: connection refused"


def test_default_model_factory_for_ollama() -> None:
    model = default_model_factory(Settings(reasoning_effort="none"), [])
    assert type(model).__name__ == "ChatOllama"
    assert model.model == "qwen3:8b" and model.num_ctx == 16_384  # type: ignore[attr-defined]
    assert model.client_kwargs == {"timeout": 120}  # type: ignore[attr-defined]
    assert model.reasoning is False  # type: ignore[attr-defined]
    assert model.num_predict == 4096  # type: ignore[attr-defined]
    openai_model = default_model_factory(Settings(model="openai:gpt-6-luna"), [])
    assert type(openai_model).__name__ == "ChatOpenAI"
    assert openai_model.max_tokens == 4096  # type: ignore[attr-defined]


def _transport(*answers: int | Exception) -> tuple[RetryTransport, list[int]]:
    """A RetryTransport over a fake server that gives these answers in order, then 200."""
    calls: list[int] = []
    queue = list(answers)

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(len(calls))
        answer = queue.pop(0) if queue else 200
        if isinstance(answer, Exception):
            raise answer
        return httpx.Response(answer, content=_OLLAMA_REPLY if answer == 200 else b"busy")

    return RetryTransport(2, httpx.MockTransport(handler), pause=0), calls


_OLLAMA_REPLY = json.dumps(
    {
        "model": "qwen3:8b",
        "created_at": "2026-10-30T15:00:00Z",
        "message": {"role": "assistant", "content": "I give up."},
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 12,
        "eval_count": 3,
    }
).encode()


@pytest.mark.parametrize(
    ("answers", "calls", "status"),
    [
        ((503,), 2, 200),
        ((httpx.ConnectError("refused"), 429), 3, 200),
        ((404,), 1, 404),  # permanent: not retried
        ((500, 500, 500), 3, 500),  # retries used up: the error is passed on
    ],
)
def test_retry_transport(answers: tuple[int | Exception, ...], calls: int, status: int) -> None:
    transport, seen = _transport(*answers)
    response = transport.handle_request(httpx.Request("POST", "http://ollama/api/chat"))
    assert response.status_code == status and len(seen) == calls


def test_retry_transport_gives_up_on_connection_errors() -> None:
    transport, seen = _transport(*[httpx.ConnectError("refused")] * 3)
    with pytest.raises(httpx.ConnectError):
        transport.handle_request(httpx.Request("POST", "http://ollama/api/chat"))
    assert len(seen) == 3


def test_ollama_episode_survives_a_transient_error(tmp_path: Path) -> None:
    from langchain_ollama import ChatOllama

    transport, seen = _transport(503)

    def factory(settings: Settings, callbacks: list) -> ChatOllama:  # type: ignore[type-arg]
        return ChatOllama(
            model="qwen3:8b", callbacks=callbacks, sync_client_kwargs={"transport": transport}
        )

    spec = RunSpec.build(["loop"], ["L1"], "dev", only=[1000], known=ARCHS)
    outcome = execute(
        spec, Settings(), model_factory=factory, architectures=ARCHS, results_dir=tmp_path
    )
    (row,) = _rows(outcome)
    assert row.status == "completed" and row.end_reason == "stopped" and row.llm_calls == 1
    assert row.input_tokens == 12 and len(seen) == 2


def test_ollama_model_gets_the_retry_transport() -> None:
    model = default_model_factory(Settings(max_retries=3), [])
    transport = model.sync_client_kwargs["transport"]  # type: ignore[attr-defined]
    assert isinstance(transport, RetryTransport) and transport.retries == 3
