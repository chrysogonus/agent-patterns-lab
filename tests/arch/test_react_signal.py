"""A1 ReAct on the signal trace, unchanged (specs/009 FR-021)."""

from langchain_core.messages import BaseMessage, HumanMessage

from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.signal_trace import generate
from apl.signal_trace.strategy import reference_run
from tests.runner.scripted import Strategy, play_calls, scripted_factory


def _reference_calls(level: str, seed: int, submit: int | None = None) -> Strategy:
    probes, found = reference_run(generate(level, seed))
    calls = [("probe", {"segment": k}) for k, _ in probes]
    return play_calls([*calls, ("submit", {"segment": found if submit is None else submit})])


def _play(strategy: Strategy, level: str = "T2") -> EpisodeResult:
    key = EpisodeKey("react", level, 1000, 1)
    return play_episode(
        key, "test", "dev", Settings(), registry.load("react"), scripted_factory(strategy),
        problem="signal",
    )  # fmt: skip


def test_react_finds_the_break_with_the_reference_probes() -> None:
    seen: list[list[BaseMessage]] = []
    inner = _reference_calls("T2", 1000)

    def strategy(messages: list[BaseMessage]):  # type: ignore[no-untyped-def]
        seen.append(list(messages))
        return inner(messages)

    row = _play(strategy).row
    assert row.problem == "signal" and row.status == "completed" and row.success
    assert row.steps is not None and row.steps <= row.optimal_steps == 7
    first = seen[0][1]
    assert isinstance(first, HumanMessage) and '"runs"' in str(first.content)


def test_a_wrong_submission_fails() -> None:
    pipe = generate("T2", 1000)
    wrong = pipe.broken % 64 + 1
    row = _play(_reference_calls("T2", 1000, submit=wrong)).row
    assert not row.success and row.end_reason == "submitted"
