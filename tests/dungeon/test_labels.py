import pytest

from apl.dungeon import LEVELS, generate
from apl.dungeon.generator import LABEL_POOL


def test_pool_is_large_enough() -> None:
    assert len(LABEL_POOL) >= 100
    assert len(set(LABEL_POOL)) == len(LABEL_POOL)


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_labels_unique_reproducible_and_spread(level: str) -> None:
    seen: dict[tuple[int, int], set[str]] = {}
    for seed in range(100):
        labels = generate(level, seed).layout.labels
        assert len(set(labels.values())) == len(labels)
        assert set(labels.values()) <= set(LABEL_POOL)
        assert generate(level, seed).layout.labels == labels
        for pos, label in labels.items():
            seen.setdefault(pos, set()).add(label)
    # A fixed mapping from position to label would give each position one label.
    assert min(len(s) for s in seen.values()) >= 10
