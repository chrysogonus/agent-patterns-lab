"""The reference walk (specs/005 SC-003, research R8)."""

import pytest

from apl.survey import DEV_SEEDS, TEST_SEEDS, generate, start_episode
from apl.survey.walk import snake


def test_snake_on_a_3x3_field() -> None:
    assert snake(3) == (
        "east", "east", "south", "west", "west", "south", "east", "east",
    )  # fmt: skip


@pytest.mark.parametrize("level", ["S1", "S2", "S3"])
def test_the_walk_is_legal_and_enters_every_cell(level: str) -> None:
    for seed in [*DEV_SEEDS, *TEST_SEEDS]:
        field = generate(level, seed)
        cell, seen = field.start, {field.start}
        for direction in field.walk:
            nxt = field.neighbor(cell, direction)
            assert nxt is not None, f"{level} {seed}: {direction} from {cell} is blocked"
            cell = nxt
            seen.add(cell)
        assert seen == set(field.all_cells())
        assert field.reference_steps == len(field.walk) + 1
        assert field.budget == 3 * field.reference_steps
        if level == "S3":
            assert not field.reference_is_optimal
        else:
            assert field.reference_is_optimal and field.reference_steps == field.size**2


@pytest.mark.parametrize("level", ["S1", "S2", "S3"])
def test_following_the_walk_and_submitting_succeeds(level: str) -> None:
    field = generate(level, 1000)
    episode = start_episode(field)
    for direction in field.walk:
        assert episode.move(direction).ok
    assert episode.submit(field.true_total).ok
    outcome = episode.outcome()
    assert outcome.success and outcome.steps == field.reference_steps
    assert outcome.cells_seen == field.cells
