from apl.dungeon import DEV_SEEDS, TEST_SEEDS


def test_seed_sets() -> None:
    assert len(DEV_SEEDS) == 10
    assert len(TEST_SEEDS) == 20
    assert set(DEV_SEEDS).isdisjoint(TEST_SEEDS)
