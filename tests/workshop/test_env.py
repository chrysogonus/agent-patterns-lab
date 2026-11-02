"""One workshop episode (specs/011 data-model.md "Episode", contracts/workshop-tools.md)."""

from typing import Any

from apl.workshop.env import start_episode
from apl.workshop.plans import reference_use
from tests.workshop.lantern import REFERENCE, STOCK, Call, lantern, play

GREEDY_TO_STUCK: list[Call] = [
    ("inspect", {"item": "lantern"}),
    ("inspect", {"item": "frame"}),
    ("inspect", {"item": "iron bar"}),
    ("gather", {"item": "coal"}),
    ("gather", {"item": "iron ore"}),
    ("craft", {"item": "iron bar", "recipe": 1}),
]


def _j(value: Any) -> Any:
    """A result or outcome as JSON-like data, typed loosely for the checks."""
    return value.to_dict()


def test_the_start_view_is_free_and_equals_look() -> None:
    episode = start_episode(lantern())
    view = _j(episode.describe())
    assert view == {"goal": "lantern", "stock": STOCK, "inventory": {}}
    assert list(view["stock"]) == sorted(STOCK) and episode.steps == 0
    assert _j(episode.look())["data"] == view and episode.steps == 1


def test_inspect() -> None:
    episode = start_episode(lantern())
    assert _j(episode.inspect("frame"))["data"] == {
        "item": "frame", "recipes": [["iron bar"], ["wood", "resin"]],
    }  # fmt: skip
    assert _j(episode.inspect("coal"))["data"] == {"item": "coal", "raw": True}
    bad = _j(episode.inspect("nails"))
    assert bad["error"] == {"code": "unknown_item", "message": "'nails' is not an item here."}
    assert episode.steps == 3 and episode.invalid_actions == 1


def test_gather() -> None:
    episode = start_episode(lantern())
    assert _j(episode.gather("coal"))["data"] == {
        "gathered": "coal", "stock": 0, "inventory": {"coal": 1},
    }  # fmt: skip
    assert _j(episode.gather("coal"))["error"] == {
        "code": "out_of_stock", "message": "There is no coal left in the stock.",
    }  # fmt: skip
    assert _j(episode.gather("frame"))["error"] == {
        "code": "not_raw", "message": "'frame' is crafted, not gathered.",
    }  # fmt: skip
    assert _j(episode.gather(None))["error"]["code"] == "unknown_item"
    assert episode.invalid_actions == 3


def test_a_failed_craft_shows_no_recipe_before_inspecting() -> None:
    episode = start_episode(lantern())
    assert _j(episode.craft("lantern", 1))["error"] == {
        "code": "missing_inputs", "message": "Missing inputs for lantern (recipe 1).",
    }  # fmt: skip
    assert _j(episode.craft("frame", 3))["error"] == {
        "code": "no_such_recipe", "message": "'frame' has no recipe 3.",
    }  # fmt: skip
    assert (
        _j(episode.craft("frame", 2))["error"]["message"] == "Missing inputs for frame (recipe 2)."
    )


def test_craft_and_its_errors() -> None:
    episode = start_episode(lantern())
    episode.inspect("frame")
    episode.gather("wood")
    assert _j(episode.craft("frame", 2))["error"] == {
        "code": "missing_inputs", "message": "Missing for frame (recipe 2): resin.",
    }  # fmt: skip
    episode.gather("resin")
    assert _j(episode.craft("frame", "2"))["data"] == {
        "crafted": "frame", "recipe": 2, "inventory": {"frame": 1},
    }  # fmt: skip
    assert _j(episode.craft("frame", 3))["error"] == {
        "code": "no_such_recipe", "message": "'frame' has 2 recipes; recipe 3 does not exist.",
    }  # fmt: skip
    assert _j(episode.craft("coal", 1))["error"] == {
        "code": "no_such_recipe", "message": "'coal' is a raw material; gather it.",
    }  # fmt: skip
    for bad in (0, "x", True, None, 1.5, "12"):
        assert _j(episode.craft("lens", bad))["error"]["code"] == "no_such_recipe"
    assert _j(episode.craft("nails", 1))["error"]["code"] == "unknown_item"
    assert episode.crafted == 1 and episode.inventory == {"frame": 1}


def test_the_goal_ends_the_episode() -> None:
    episode = start_episode(lantern())
    play(episode, REFERENCE)
    last = _j(episode.log[-1].result)["data"]
    assert last["crafted"] == "lantern" and last["goal"] is True
    outcome = episode.outcome()
    assert outcome.success and str(outcome.end_reason) == "goal" and outcome.steps == 15
    assert outcome.wasted == 0 and outcome.inspected == 5 and outcome.crafted == 5


def test_getting_stuck_ends_the_episode() -> None:
    episode = start_episode(lantern())
    play(episode, GREEDY_TO_STUCK)
    last = _j(episode.log[-1].result)
    assert last["ok"] and last["data"] == {
        "crafted": "iron bar", "recipe": 1, "inventory": {"iron bar": 1}, "stuck": True,
    }  # fmt: skip
    outcome = episode.outcome()
    assert str(outcome.end_reason) == "stuck" and outcome.stuck and not outcome.success
    assert outcome.wasted == 1  # the reference never crafts an iron bar


def test_a_retrying_architecture_restarts_when_stuck() -> None:
    episode = start_episode(lantern())
    episode.max_attempts = 3
    restarts: list[int] = []
    episode.on_restart = lambda: restarts.append(episode.attempt)
    play(episode, GREEDY_TO_STUCK)
    data = _j(episode.log[-1].result)["data"]
    assert data["stuck"] is True and data["attempts_left"] == 2
    assert restarts == [2] and episode.attempt == 2 and episode.end_reason is None
    assert episode.stock == STOCK and episode.inventory == {}
    assert episode.steps == 6 and episode.wasted == 1
    play(episode, GREEDY_TO_STUCK)  # attempt 2: stuck again, with one attempt left
    play(episode, GREEDY_TO_STUCK)  # attempt 3: stuck for good
    assert str(episode.end_reason) == "stuck" and episode.wasted == 3 and restarts == [2, 3]
    assert episode.outcome().attempts == 3


def test_waste_counts_per_item_and_attempt() -> None:
    episode = start_episode(lantern())
    calls: list[Call] = [
        ("gather", {"item": "sand"}),
        ("gather", {"item": "coal"}),
        ("craft", {"item": "glass", "recipe": 1}),
    ]
    play(episode, calls)
    assert episode.wasted == 0  # the reference crafts glass from coal too
    assert reference_use(lantern())[("glass", "coal")] == 1


def test_the_budget_and_the_goal_on_the_last_step() -> None:
    w = lantern()
    episode = start_episode(w)
    for _ in range(w.budget):
        episode.look()
    assert str(episode.end_reason) == "budget" and episode.outcome().budget_hit
    episode = start_episode(w)
    for _ in range(w.budget - len(REFERENCE)):
        episode.look()
    play(episode, REFERENCE)
    assert episode.outcome().success and episode.steps == w.budget


def test_calls_after_the_end_and_unknown_tools() -> None:
    episode = start_episode(lantern())
    assert _j(episode.unknown("build"))["error"] == {
        "code": "unknown_tool",
        "message": "There is no tool named 'build'. The tools are look, inspect, gather and craft.",
    }
    episode.stop()
    assert str(episode.end_reason) == "stopped"
    assert _j(episode.look())["error"]["code"] == "episode_over" and episode.steps == 1
    assert episode.log[-1].step is None


def test_the_outcome_and_waste_rebuilt_from_the_log() -> None:
    w = lantern()
    episode = start_episode(w)
    episode.max_attempts = 2
    play(episode, [*GREEDY_TO_STUCK, *REFERENCE])
    data = _j(episode.outcome())
    for key in ("stuck", "wasted", "inspected", "crafted", "reference_is_optimal", "attempts"):
        assert key in data
    # Rebuild the waste from the saved log alone (SC-006).
    allowed = reference_use(w)
    used: dict[tuple[str, str], int] = {}
    wasted = 0
    for entry in data["log"]:
        found = entry["result"]["data"]
        if entry["action"]["tool"] != "craft" or not entry["result"]["ok"]:
            continue
        item, k = found["crafted"], found["recipe"]
        for raw in w.recipes[item][k - 1]:
            if raw in w.scarce:
                used[item, raw] = used.get((item, raw), 0) + 1
                wasted += used[item, raw] > allowed.get((item, raw), 0)
        if found.get("attempts_left") is not None:
            used = {}
    assert wasted == data["wasted"] == 1 and data["success"]
