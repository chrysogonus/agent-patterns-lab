"""The workshop's plans and stuck check on the hand-built lantern (specs/011 research R5–R8)."""

from apl.workshop.plans import (
    feasible,
    greedy_calls,
    planner_calls,
    reference_calls,
    reference_use,
)
from tests.workshop.lantern import REFERENCE, STOCK, lantern


def test_feasible_follows_what_is_left() -> None:
    w = lantern()
    assert feasible(w, STOCK, {})
    after_iron_bar = {**STOCK, "coal": 0, "iron ore": 1}
    assert not feasible(w, after_iron_bar, {"iron bar": 1})  # the coal is inside the iron bar
    assert feasible(w, {**STOCK, "coal": 0}, {"glass": 1})  # the glass was made already
    assert feasible(w, {k: 0 for k in STOCK}, {"frame": 1, "lens": 1, "oil": 1})


def test_the_reference_plan() -> None:
    w = lantern()
    assert reference_calls(w) == REFERENCE
    assert w.reference == 15 and w.budget == 45
    assert reference_use(w) == {
        ("frame", "wood"): 1, ("frame", "resin"): 1, ("glass", "sand"): 1, ("glass", "coal"): 1,
        ("oil", "seeds"): 1,
    }  # fmt: skip


def test_the_greedy_plan_takes_the_first_recipe() -> None:
    calls = greedy_calls(lantern())
    assert calls[:6] == [
        ("inspect", {"item": "lantern"}),
        ("inspect", {"item": "frame"}),
        ("inspect", {"item": "iron bar"}),
        ("gather", {"item": "coal"}),
        ("gather", {"item": "iron ore"}),
        ("craft", {"item": "iron bar", "recipe": 1}),
    ]
    assert ("craft", {"item": "frame", "recipe": 1}) in calls


def test_the_planner_inspects_everything_first() -> None:
    calls = planner_calls(lantern())
    first_gather = next(i for i, (name, _) in enumerate(calls) if name == "gather")
    inspected = {args["item"] for name, args in calls[:first_gather] if name == "inspect"}
    assert inspected == {"lantern", "frame", "iron bar", "lens", "glass", "oil"}
    assert ("craft", {"item": "frame", "recipe": 2}) in calls
    assert all(name != "inspect" for name, _ in calls[first_gather:])
