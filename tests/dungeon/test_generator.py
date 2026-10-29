import hashlib
import json
import time

import pytest

from apl.dungeon import DEV_SEEDS, LEVELS, TEST_SEEDS, check_level_rules, generate, solve
from apl.dungeon.model import Dungeon

EXTRA_SEEDS = range(10_000, 11_000)


def fingerprint(dungeon: Dungeon) -> str:
    return hashlib.sha256(json.dumps(dungeon.to_dict(), sort_keys=True).encode()).hexdigest()


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_every_dungeon_meets_the_rules_and_is_solvable(level: str) -> None:
    for seed in [*DEV_SEEDS, *TEST_SEEDS, *EXTRA_SEEDS]:
        dungeon = generate(level, seed)
        assert check_level_rules(dungeon.layout, LEVELS[level]) == [], (level, seed)
        assert solve(dungeon.layout) == dungeon.solution, (level, seed)


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_same_seed_same_dungeon(level: str) -> None:
    for seed in DEV_SEEDS:
        assert generate(level, seed).to_dict() == generate(level, seed).to_dict()


# Pinned once, after the first green run. A change here means the dungeons changed, which
# invalidates earlier results (constitution, Experiment Setup).
GOLDEN = {
    ("L1", 1000): "86a297771d32af7643ff9af189e9946317218cd403922fd1f5825873122a8733",
    ("L1", 2000): "09851dac4d49386ebe2c4ba273c89e03d78190a0299b5c923bdd94393f7f8542",
    ("L2", 1000): "fe412144a2237bd31b252d3c358f91cbac9427595809cbe3102fa6c7ebc867c5",
    ("L2", 2000): "3effaa38ba96c2622503a0245b5abd8821a936de6687c66b3d5f1de8b520eb20",
    ("L3", 1000): "f101b9dd482b4f3800a727997e636650566ae75986b0db9e64e566e00f5bfb20",
    ("L3", 2000): "317e024a76da9952fade24881208765d74c3cf0012ac6ea9d5b8960a2d4718b9",
}


@pytest.mark.parametrize(("level", "seed"), sorted(GOLDEN))
def test_golden_fingerprints(level: str, seed: int) -> None:
    assert fingerprint(generate(level, seed)) == GOLDEN[(level, seed)]


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_dungeons_vary(level: str) -> None:
    assert len({fingerprint(generate(level, seed)) for seed in range(100)}) >= 95


@pytest.mark.parametrize(("level", "seed"), [("L9", 1), ("L1", -1), ("L1", 1.5), ("L1", True)])
def test_invalid_input_is_refused(level: str, seed: object) -> None:
    with pytest.raises(ValueError):
        generate(level, seed)  # type: ignore[arg-type]


def test_seed_sets_are_fast() -> None:
    started = time.perf_counter()
    for level in LEVELS:
        for seed in [*DEV_SEEDS, *TEST_SEEDS]:
            solve(generate(level, seed).layout)
    assert time.perf_counter() - started < 10
