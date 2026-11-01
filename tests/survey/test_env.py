"""One survey episode: tools, errors, scouts, ending, turns (specs/005 R7, R11)."""

import itertools

from apl.survey import generate, start_episode
from apl.survey.model import Field

VIEW = {"cell", "deposit", "exits", "columns", "rows"}


def _open_field() -> Field:
    return generate("S1", 1000)


def test_views_have_a_fixed_shape() -> None:
    episode = start_episode(_open_field())
    data = episode.look().to_dict()
    assert data["ok"] and isinstance(data["data"], dict) and set(data["data"]) == VIEW
    view = episode.describe()
    assert view.cell == "A1" and view.exits == ("east", "south")
    assert (view.columns, view.rows) == (6, 6)
    moved = episode.move("east")
    assert moved.ok and moved.to_dict()["data"]["cell"] == "B1"  # type: ignore[index]
    assert episode.describe().exits == ("east", "south", "west")


def test_walls_edges_and_bad_directions_cost_a_step() -> None:
    episode = start_episode(_open_field())
    result = episode.move("north")
    assert not result.ok and result.error is not None
    assert (str(result.error.code), result.error.message) == (
        "wall",
        "There is a wall to the north.",
    )
    bad = episode.move("up")
    assert bad.error is not None and str(bad.error.code) == "invalid_direction"
    assert bad.error.message == "'up' is not a direction; use north, east, south or west."
    assert episode.steps == 2 and episode.invalid_actions == 2


def test_walls_inside_the_field() -> None:
    field = generate("S3", 1000)
    (a, b) = sorted(next(iter(field.walls)))
    direction = "east" if b[0] > a[0] else "south"
    assert field.neighbor(a, direction) is None
    assert direction not in field.exits(a)


def test_submit_accepts_whole_numbers_only() -> None:
    episode = start_episode(_open_field())
    for raw in (-1, "about 12", 1.5, True, None, "-3", ""):
        result = episode.submit(raw)
        assert not result.ok and result.error is not None
        assert str(result.error.code) == "invalid_total"
    assert episode.end_reason is None and episode.steps == 7
    assert episode.submit("6").ok
    assert str(episode.end_reason) == "submitted" and episode.outcome().submitted_total == 6


def test_a_right_total_succeeds_and_a_wrong_one_fails() -> None:
    right = start_episode(_open_field())
    right.submit(6)
    assert right.outcome().success
    wrong = start_episode(_open_field())
    wrong.submit(5)
    outcome = wrong.outcome()
    assert not outcome.success and outcome.submitted_total == 5 and outcome.true_total == 6


def test_the_budget_ends_the_episode_and_later_calls_are_not_counted() -> None:
    field = _open_field()
    episode = start_episode(field)
    for _ in range(field.budget):
        episode.look()
    assert str(episode.end_reason) == "budget" and episode.outcome().budget_hit
    late = episode.look()
    assert late.error is not None and str(late.error.code) == "episode_over"
    assert episode.log[-1].step is None and episode.steps == field.budget


def test_a_submission_on_the_last_step_counts() -> None:
    field = _open_field()
    episode = start_episode(field)
    for _ in range(field.budget - 1):
        episode.look()
    episode.submit(6)
    assert str(episode.end_reason) == "submitted" and episode.outcome().success


def test_stop_and_unknown_tools() -> None:
    episode = start_episode(_open_field())
    result = episode.unknown("scan")
    assert result.error is not None and str(result.error.code) == "unknown_tool"
    assert (
        result.error.message
        == "There is no tool named 'scan'. The tools are look, move and submit."
    )
    episode.stop()
    assert str(episode.end_reason) == "stopped" and episode.outcome().submitted_total is None


def test_reentering_a_cell_shows_the_same_view() -> None:
    episode = start_episode(_open_field())
    first = episode.describe()
    episode.move("east")
    episode.move("west")
    assert episode.describe() == first


def test_scouts_share_the_budget_and_the_seen_cells() -> None:
    episode = start_episode(_open_field())
    numbers = [episode.add_scout() for _ in range(4)]
    assert numbers == [1, 2, 3, None] and episode.steps == 0
    episode.move("east", scout=1)
    episode.move("south", scout=2)
    assert episode.describe(1).cell == "B1" and episode.describe(2).cell == "A2"
    assert episode.describe(0).cell == "A1"
    episode.stop()
    outcome = episode.outcome()
    assert outcome.cells_seen == 3 and outcome.scouts == 2 and outcome.steps == 2


def test_parallel_turns_count_distinct_turns() -> None:
    episode = start_episode(_open_field())
    assert episode.look().ok
    episode.stop()
    assert episode.outcome().parallel_turns == 1  # without a turn source: one per step
    episode = start_episode(_open_field())
    episode.add_scout()
    turns = itertools.chain([1, 1, 2, 2, 3])
    episode.turn_source = lambda: next(turns)
    episode.move("east")
    episode.move("south", scout=1)
    episode.move("east")
    episode.move("south", scout=1)
    episode.look()
    episode.stop()
    outcome = episode.outcome()
    assert outcome.steps == 5 and outcome.parallel_turns == 3
    assert [e.turn for e in episode.log] == [1, 1, 2, 2, 3]
