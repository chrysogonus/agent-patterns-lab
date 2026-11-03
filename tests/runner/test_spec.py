"""Run descriptions, the episode matrix and the dry run's upper bounds (research R10)."""

import pytest

from apl.dungeon import DEV_SEEDS, generate
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey, RunSpec


def _spec(**kwargs: object) -> RunSpec:
    args: dict[str, object] = {"architectures": ["react"], "levels": ["L2"], "seed_set": "dev"}
    return RunSpec.build(**{**args, **kwargs})  # type: ignore[arg-type]


def test_matrix_order_and_size() -> None:
    spec = _spec(repeats=3)
    episodes = list(spec.episodes())
    assert len(episodes) == 30  # US1/AC1: 10 seeds × 3 repeats
    assert episodes[:4] == [
        EpisodeKey("react", "L2", 1000, 1),
        EpisodeKey("react", "L2", 1000, 2),
        EpisodeKey("react", "L2", 1000, 3),
        EpisodeKey("react", "L2", 1001, 1),
    ]
    # Level, seed, repeat, then architecture: every architecture plays a dungeon in turn (R10).
    spec = RunSpec.build(["a", "b"], ["L1", "L2"], "dev", limit=1, known={"a", "b"})
    assert [(k.arch, k.level) for k in spec.episodes()] == [
        ("a", "L1"),
        ("b", "L1"),
        ("a", "L2"),
        ("b", "L2"),
    ]


def test_the_m4_run_has_21_episodes() -> None:  # specs/004 FR-011
    names = ["react", "mapstate", "mapstate_routes", "hybrid", "fanout", "rounds", "blackboard"]
    spec = RunSpec.build(names, ["all"], "dev", limit=1)
    keys = list(spec.episodes())
    assert len(keys) == 21 and {k.seed for k in keys} == {1000}
    assert [k.arch for k in keys[:7]] == names and {k.level for k in keys[:7]} == {"L1"}


def test_known_architectures_are_checked() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "registered: blackboard, fanout, hybrid, mapstate, mapstate_routes, plan_execute, "
            "react, reflexion, retry, rounds, supervisor"
        ),
    ):
        _spec(architectures=["nope"])
    spec = RunSpec.build(["loop"], ["L1"], "dev", known={"loop"})
    assert spec.architectures == ("loop",)


def test_level_and_seed_selection() -> None:
    assert _spec(levels=["all"]).levels == ("L1", "L2", "L3")
    assert _spec(limit=2).seeds == (1000, 1001)
    assert _spec(only=[1000, 1004]).seeds == (1000, 1004)
    assert _spec().seeds == tuple(DEV_SEEDS)
    assert _spec(seed_set="test").seeds[0] == 2000


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"only": [5]}, "not in the dev seeds"),
        ({"limit": 0}, "between 1 and 10"),
        ({"limit": 11}, "between 1 and 10"),
        ({"limit": 2, "only": [1000]}, "not both"),
        ({"levels": ["L2", "L2"]}, "duplicate"),
        ({"levels": ["L9"]}, "unknown level"),
        ({"architectures": ["react", "react"]}, "duplicate"),
        ({"repeats": 0}, "at least 1"),
        ({"seed_set": "train"}, "dev or test"),
    ],
)
def test_invalid_descriptions(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _spec(**kwargs)


def test_upper_bounds() -> None:
    spec = _spec(levels=["all"], limit=2)
    budgets = sum(generate(level, seed).budget for level in spec.levels for seed in spec.seeds)
    bounds = spec.upper_bounds(Settings())
    assert bounds.calls == budgets + 6 == 450
    assert bounds.tokens == 6 * 2_000_000
    assert bounds.cost is None
    priced = spec.upper_bounds(Settings(price_input=0.10, price_output=0.50))
    assert priced.cost == pytest.approx(6.00)


def test_the_problem_defaults_to_the_dungeon() -> None:
    spec = _spec()
    assert spec.problem == "dungeon"
    assert RunSpec.build(["react"], ["all"], "dev", problem="dungeon").levels == ("L1", "L2", "L3")


def test_an_architecture_must_play_the_problem() -> None:
    supports = {"react": frozenset({"dungeon", "survey"}), "hybrid": frozenset({"dungeon"})}
    with pytest.raises(
        ValueError, match=r"^hybrid does not play the survey problem \(it plays: dungeon\)$"
    ):
        RunSpec.build(
            ["react", "hybrid"], ["all"], "dev", problem="survey", supports=supports,
            known={"react", "hybrid"},
        )  # fmt: skip


def test_an_unknown_problem_is_refused_when_planning() -> None:
    with pytest.raises(ValueError, match="unknown problem 'chess'"):
        RunSpec.build(["react"], ["all"], "dev", problem="chess")
