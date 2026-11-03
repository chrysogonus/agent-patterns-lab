"""What a rune-floor result can show (specs/010 research R15, contracts/rune-tools.md)."""

import dataclasses
import json
import random
from typing import Any

import pytest

from apl.rune import DEV_SEEDS, LEVELS, generate, start_episode
from apl.rune.model import Rule
from apl.rune.tools import AgentTools

ENVELOPE = {"ok", "error", "data"}
SHAPES = [
    {"columns", "rows", "start", "goal", "position", "floor"},
    {"position", "color"},
    {"trap", "color", "position"},
    {"trap", "color", "position", "attempts_left"},
    {"position", "goal"},
]
FORBIDDEN = ("cycle", "rule", "odd", "even", "reference")


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_results_have_fixed_shapes_and_never_name_the_rule(level: str) -> None:
    rng = random.Random(f"rune-boundary:{level}")
    for seed in DEV_SEEDS:
        episode = start_episode(generate(level, seed))
        episode.max_attempts = 3
        tools = AgentTools(episode)
        for _ in range(300):
            if rng.random() < 0.1:
                result = tools.look()
            else:
                result = tools.move(rng.choice(["north", "east", "south", "west", "up", 7]))
            data = _j(result)
            assert set(data) == ENVELOPE
            text = json.dumps(data)
            assert not any(word in text for word in FORBIDDEN), text
            if data["ok"]:
                assert set(data["data"]) in SHAPES
            else:
                assert set(data["error"]) == {"code", "message"}
            if episode.end_reason is not None:
                break


def test_the_start_and_look_do_not_depend_on_the_rule() -> None:
    floor = generate("R1", 1000)
    rules = [
        floor.rule,
        Rule("cycle", ("yellow", "green", "blue")),
        Rule("rows", ("red", "blue")),
        Rule("none", (), frozenset({(1, 1)})),
    ]
    views = set()
    for rule in rules:
        other = dataclasses.replace(floor, rule=rule)
        tools = AgentTools(start_episode(other))
        views.add(json.dumps(_j(tools.start)))
        views.add(json.dumps(_j(tools.look())))
    assert len(views) == 1


def test_agent_tools_expose_only_the_tools() -> None:
    public = {
        n for n in dir(AgentTools(start_episode(generate("R0", 1000)))) if not n.startswith("_")
    }
    assert public == {"start", "look", "move"}


def _j(value: Any) -> Any:
    """A result or outcome as JSON-like data, typed loosely for the checks."""
    return value.to_dict()
