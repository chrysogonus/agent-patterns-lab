"""Workshops from a level and a seed (specs/011 research R3, R4, R6). Runner side only."""

import dataclasses
import random

from apl.workshop.model import CRAFTABLE_NAMES, LEVELS, RAW_NAMES, Workshop, WorkshopLevel
from apl.workshop.plans import ends_stuck, feasible, greedy_calls, reference_calls

MAX_TRIES = 1000
PLENTIFUL = 4  # plentiful raw materials per workshop
MAX_CRAFTABLE_INPUTS = 3


def generate(level: str, seed: int) -> Workshop:
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r} (levels: {', '.join(LEVELS)})")
    spec = LEVELS[level]
    rng = random.Random(f"workshop:{level}:{seed}")
    for _ in range(MAX_TRIES):
        found = _draw(spec, seed, rng)
        if found is not None:
            return found
    raise RuntimeError(f"no {level} workshop for seed {seed} in {MAX_TRIES} tries")


def _draw(spec: WorkshopLevel, seed: int, rng: random.Random) -> Workshop | None:
    names = rng.sample(CRAFTABLE_NAMES, spec.craftables + spec.conflicts)
    raws = rng.sample(RAW_NAMES, PLENTIFUL + spec.conflicts)
    plenty, scarce = raws[:PLENTIFUL], raws[PLENTIFUL:]
    goal, pool, extra = names[0], names[1 : spec.craftables], names[spec.craftables :]
    inputs: dict[str, list[str]] = {goal: []}
    level_of, parent = {goal: 0}, {}
    # A chain reaches the level's depth; the rest attach anywhere with room (research R3).
    for name in pool:
        chain = len(inputs) < spec.depth
        if chain:
            host = next(n for n in inputs if level_of[n] == len(inputs) - 1)
        else:
            room = [
                n
                for n in inputs
                if level_of[n] < spec.depth - 1
                and len([i for i in inputs[n] if i in inputs]) < MAX_CRAFTABLE_INPUTS
            ]
            host = rng.choice(room)
        inputs[name] = []
        level_of[name], parent[name] = level_of[host] + 1, host
        inputs[host].append(name)
    for name, held in inputs.items():
        leaf = not held
        inputs[name] = held + rng.sample(plenty, rng.choice([1, 2] if leaf else [0, 1]))
    order: list[str] = []

    def walk(item: str) -> None:
        order.append(item)
        for i in inputs[item]:
            if i in inputs:
                walk(i)

    walk(goal)

    def ancestors(item: str) -> set[str]:
        out = set()
        while item in parent:
            item = parent[item]
            out.add(item)
        return out

    first: dict[str, list[str]] = {}  # tempting items' new first recipes
    for k in range(spec.conflicts):
        s, m = scarce[k], extra[k]
        pairs = [
            (t, x)
            for t in order[1:]
            for x in order[order.index(t) + 1 :]
            if t not in ancestors(x)
            and x not in first
            and t not in first
            and not ancestors(x) & set(first)
            and not any(t in ancestors(xx) for xx in _users(inputs, scarce[:k]))
        ]
        if not pairs:
            return None
        t, x = rng.choice(pairs)
        inputs[x].append(s)
        first[t] = [m] + ([rng.choice(plenty)] if rng.random() < 0.5 else [])
        inputs[m] = [s, rng.choice(plenty)]
    recipes: dict[str, tuple[tuple[str, ...], ...]] = {}
    for item, held in inputs.items():
        recipes[item] = (tuple(first[item]), tuple(held)) if item in first else (tuple(held),)
    choice = {t: 2 for t in first}
    if spec.conflicts == 0:  # W1: one harmless second recipe, listed second (research R4)
        item = rng.choice(order[1:])
        recipes[item] = (recipes[item][0], tuple(rng.sample(plenty, 2)))
        choice[item] = 1
    shell = Workshop(None, seed, goal, recipes, {r: 0 for r in raws}, frozenset(scarce), choice, 0)
    use: dict[str, int] = {}
    for name, args in reference_calls(shell):
        if name == "gather":
            use[str(args["item"])] = use.get(str(args["item"]), 0) + 1
    stock = {r: use.get(r, 0) + (0 if r in scarce else rng.randint(1, 2)) for r in sorted(raws)}
    workshop = dataclasses.replace(shell, level=spec, stock=stock)
    workshop = dataclasses.replace(workshop, reference=len(reference_calls(workshop)))
    if not feasible(workshop, stock, {}) or any(stock[s] != 1 for s in scarce):
        return None
    if ends_stuck(workshop, greedy_calls(workshop)) != (spec.conflicts > 0):
        return None
    return workshop


def _users(inputs: dict[str, list[str]], scarce: list[str]) -> list[str]:
    """The craftables that already need one of these scarce materials."""
    return [item for item, held in inputs.items() if set(held) & set(scarce)]
