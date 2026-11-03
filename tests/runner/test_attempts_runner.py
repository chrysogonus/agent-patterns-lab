"""Attempts in the kit, the runner, the rows and the report (specs/007 contracts/attempts.md)."""

from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from apl.kit import Kit
from apl.runner import registry
from apl.runner.episode import play_episode
from apl.runner.meter import LEAD_ROLES
from apl.runner.report import load_run, render
from apl.runner.results import EpisodeRow
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from tests.runner.scripted import scripted_factory, text_answer, tool_calls
from tests.runner.test_report import _row, _write

SEEN: dict[str, object] = {}


def _retry_once(kit: Kit) -> None:
    """Calls look, restarts once, calls look again, then stops."""
    look = kit.model.invoke([HumanMessage("go")])
    assert isinstance(look, AIMessage)
    SEEN["max_attempts"] = kit.max_attempts
    kit.tool_node({"messages": [tool_calls(("look", {}))]})
    SEEN["restart"] = kit.restart()
    kit.tool_node({"messages": [tool_calls(("look", {}))]})


def _play(arch: str, problem: str) -> EpisodeRow:
    level = "S1" if problem == "survey" else "L1"
    key = EpisodeKey(arch, level, 1000, 1)
    result = play_episode(
        key, "test", "dev", Settings(), _retry_once, scripted_factory(text_answer()),
        problem=problem,
    )  # fmt: skip
    return result.row


@pytest.mark.parametrize("problem", ["dungeon", "survey"])
def test_a_retrying_architecture_can_restart(problem: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry, "RETRYING", frozenset({"retry_double"}))
    row = _play("retry_double", problem)
    assert SEEN == {"max_attempts": 3, "restart": True}
    assert row.attempts == 2 and row.steps == 2 and row.end_reason == "stopped"


@pytest.mark.parametrize("problem", ["dungeon", "survey"])
def test_any_other_architecture_cannot(problem: str) -> None:  # FR-003
    row = _play("react", problem)
    assert SEEN == {"max_attempts": 1, "restart": False}
    assert row.attempts is None and row.steps == 2


def test_old_rows_have_no_attempts() -> None:
    row = _row(1000, 1, 8)
    assert EpisodeRow.parse(row).attempts is None
    assert EpisodeRow.parse(row | {"attempts": 2}).attempts == 2


def test_the_report_shows_attempts_only_when_there_are_some(tmp_path: Path) -> None:
    rows = [_row(1000, 1, 8, arch="mapstate"), _row(1000, 2, 8, arch="mapstate")]
    plain = render([load_run(_write(tmp_path / "a", rows, architectures=["mapstate"]))])
    assert "## Attempts" not in plain
    retried = [
        _row(1000, 1, 8, arch="reflexion", attempts=1),
        _row(1000, 2, 12, arch="reflexion", attempts=3),
        _row(1000, 3, 10, arch="reflexion", attempts=2),
        *rows,
    ]
    report = render(
        [load_run(_write(tmp_path / "b", retried, architectures=["mapstate", "reflexion"]))]
    )
    section = report[report.index("## Attempts") :]
    assert "| Arch | Level | Attempts (median) | Attempts (max) |" in section
    assert "| mapstate | L1 | 1 | 1 |" in section
    assert "| reflexion | L1 | 2 | 3 |" in section


def test_the_reflector_is_a_lead_role() -> None:
    assert "reflector" in LEAD_ROLES
