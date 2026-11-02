"""The workshop's stuck check, reference plan, scripted plans and waste (specs/011 R5–R8).

Runner side: architectures never see this module (Constitution II).
"""

import itertools
from collections.abc import Mapping

from apl.workshop.model import Recipe, Workshop

Call = tuple[str, dict[str, object]]


def alternatives(workshop: Workshop) -> list[str]:
    """The craftables with two recipes, by name."""
    return sorted(item for item, recipes in workshop.recipes.items() if len(recipes) > 1)


def _recipe(workshop: Workshop, item: str, choice: Mapping[str, int]) -> tuple[int, Recipe]:
    k = choice.get(item, 1)
    return k, workshop.recipes[item][k - 1]


def _can_make(
    workshop: Workshop, choice: Mapping[str, int], stock: Mapping[str, int], held: Mapping[str, int]
) -> bool:
    left, have = dict(stock), dict(held)

    def make(item: str) -> bool:
        if have.get(item, 0) > 0:  # a held unit is always the cheapest way
            have[item] -= 1
            return True
        if workshop.raw(item):
            if left.get(item, 0) > 0:
                left[item] -= 1
                return True
            return False
        return all(make(i) for i in _recipe(workshop, item, choice)[1])

    return make(workshop.goal)


def feasible(workshop: Workshop, stock: Mapping[str, int], held: Mapping[str, int]) -> bool:
    """Whether the goal can still be made from what is held and the stock (research R5)."""
    open_ = alternatives(workshop)
    for picks in itertools.product((1, 2), repeat=len(open_)):
        if _can_make(workshop, dict(zip(open_, picks, strict=True)), stock, held):
            return True
    return False


def _calls(workshop: Workshop, choice: Mapping[str, int], inspect: bool) -> list[Call]:
    """Depth first from the goal: inspect each craftable when first reached, gather what is
    missing, craft. A raw material or item needed twice is gathered or crafted twice."""
    calls: list[Call] = []
    seen: set[str] = set()

    def build(item: str) -> None:
        if inspect and item not in seen:
            seen.add(item)
            calls.append(("inspect", {"item": item}))
        k, recipe = _recipe(workshop, item, choice)
        for name in recipe:
            if workshop.raw(name):
                calls.append(("gather", {"item": name}))
            else:
                build(name)
        calls.append(("craft", {"item": item, "recipe": k}))

    build(workshop.goal)
    return calls


def reference_calls(workshop: Workshop) -> list[Call]:
    """The reference plan: the reference's recipe choices, inspecting what it crafts (R6)."""
    return _calls(workshop, workshop.reference_choice, inspect=True)


def greedy_calls(workshop: Workshop) -> list[Call]:
    """Inspect as it goes, depth first, always the first recipe (research R7)."""
    return _calls(workshop, {}, inspect=True)


def planner_calls(workshop: Workshop) -> list[Call]:
    """Inspect every craftable reachable through any recipe, then follow the first recipe choices
    that can make the goal from the start (research R7)."""
    order: list[str] = []
    queue = [workshop.goal]
    while queue:
        item = queue.pop(0)
        if item in order:
            continue
        order.append(item)
        queue += [i for r in workshop.recipes[item] for i in r if workshop.craftable(i)]
    open_ = alternatives(workshop)
    for picks in itertools.product((1, 2), repeat=len(open_)):
        choice = dict(zip(open_, picks, strict=True))
        if _can_make(workshop, choice, workshop.stock, {}):
            inspections: list[Call] = [("inspect", {"item": i}) for i in order]
            return inspections + _calls(workshop, choice, inspect=False)
    raise ValueError("the workshop cannot be made")


def reference_use(workshop: Workshop) -> dict[tuple[str, str], int]:
    """(item, raw material) → units the reference plan's crafts of that item consume (R8)."""
    use: dict[tuple[str, str], int] = {}
    for name, args in reference_calls(workshop):
        if name == "craft":
            item, k = str(args["item"]), int(str(args["recipe"]))
            for raw in workshop.recipes[item][k - 1]:
                if workshop.raw(raw):
                    use[item, raw] = use.get((item, raw), 0) + 1
    return use


def ends_stuck(workshop: Workshop, calls: list[Call]) -> bool:
    """Whether playing these calls from the start leaves the goal impossible before it is made
    (the generator's acceptance check; the environment keeps its own count)."""
    stock, held = dict(workshop.stock), dict[str, int]()
    for name, args in calls:
        item = str(args.get("item"))
        if name == "gather":
            if stock.get(item, 0) == 0:
                return True
            stock[item] -= 1
            held[item] = held.get(item, 0) + 1
        elif name == "craft":
            _, recipe = _recipe(workshop, item, {item: int(str(args["recipe"]))})
            for i in recipe:
                if held.get(i, 0) == 0:
                    return True
                held[i] -= 1
            held[item] = held.get(item, 0) + 1
            if item == workshop.goal:
                return False
            if not feasible(workshop, stock, held):
                return True
    return False
