"""What a workshop result can show (specs/011 research R15, contracts/workshop-tools.md)."""

import dataclasses
import json
import random
from typing import Any

import pytest

from apl.workshop import DEV_SEEDS, LEVELS, AgentTools, generate, start_episode

ENVELOPE = {"ok", "error", "data"}
SHAPES = [
    {"goal", "stock", "inventory"},
    {"item", "recipes"},
    {"item", "raw"},
    {"gathered", "stock", "inventory"},
    {"crafted", "recipe", "inventory"},
    {"crafted", "recipe", "inventory", "goal"},
    {"crafted", "recipe", "inventory", "stuck"},
    {"crafted", "recipe", "inventory", "stuck", "attempts_left"},
]
FORBIDDEN = ("scarce", "reference", "budget")


def _j(value: Any) -> Any:
    return value.to_dict()


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_results_have_fixed_shapes_and_show_only_inspected_recipes(level: str) -> None:
    rng = random.Random(f"workshop-boundary:{level}")
    for seed in DEV_SEEDS:
        w = generate(level, seed)
        episode = start_episode(w)
        episode.max_attempts = 3
        tools = AgentTools(episode)
        names = [*w.recipes, *w.stock, "nails"]
        inspected: set[str] = set()
        for _ in range(300):
            name = rng.choice(names)
            tool = rng.choice(["look", "inspect", "gather", "gather", "craft", "craft"])
            if tool == "look":
                result = tools.look()
            elif tool == "inspect":
                result = tools.inspect(name)
            elif tool == "gather":
                result = tools.gather(name)
            else:
                result = tools.craft(name, rng.choice([0, 1, 2, 3, "1"]))
            data = _j(result)
            assert set(data) == ENVELOPE
            text = json.dumps(data)
            assert not any(word in text for word in FORBIDDEN), text
            if data["ok"]:
                assert set(data["data"]) in SHAPES
                if "recipes" in data["data"] or "raw" in data["data"]:
                    inspected.add(data["data"]["item"])
                    assert tool == "inspect"
            else:
                assert set(data["error"]) == {"code", "message"}
                if tool == "craft" and name in w.recipes and name not in inspected:
                    # No input of an item not yet inspected shows in an error (FR-006).
                    message = data["error"]["message"]
                    inputs = {i for r in w.recipes[name] for i in r}
                    assert not any(f" {i}" in message for i in inputs), message
                    assert "recipes" not in message, message
            if episode.end_reason is not None:
                break


def test_the_start_and_look_do_not_depend_on_the_recipes() -> None:
    w = generate("W2", 1000)
    other = dataclasses.replace(w, recipes={**w.recipes, w.goal: (tuple(w.stock)[:1],)})
    views = set()
    for workshop in (w, other):
        tools = AgentTools(start_episode(workshop))
        views.add(json.dumps(_j(tools.start)))
        views.add(json.dumps(_j(tools.look())))
    assert len(views) == 1


def test_agent_tools_expose_only_the_tools() -> None:
    tools = AgentTools(start_episode(generate("W1", 1000)))
    assert {n for n in dir(tools) if not n.startswith("_")} == {
        "start", "look", "inspect", "gather", "craft",
    }  # fmt: skip
