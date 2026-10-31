"""A6 hybrid with the scripted model: code walks the routes, the model picks the target."""

import json
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from apl.arch.dungeon_map import DungeonMap
from apl.arch.hybrid import HYBRID_INSTRUCTIONS, options
from apl.dungeon import DEV_SEEDS, LEVELS
from apl.kit import BASE_PROMPT
from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from tests.runner.scripted import Strategy, scripted_factory


def _play(level: str, seed: int, strategy: Strategy) -> EpisodeResult:
    key = EpisodeKey("hybrid", level, seed, 1)
    return play_episode(
        key, "test", "dev", Settings(), registry.load("hybrid"), scripted_factory(strategy)
    )


def _answers(*texts: str) -> Strategy:
    """Replies with the given texts in turn, then with the last one forever."""
    queue = list(texts)
    return lambda messages: AIMessage(queue.pop(0) if len(queue) > 1 else queue[0])


def _room(
    label: str, exits: dict[str, str | None], items: list[str], held: list[str]
) -> dict[str, Any]:
    data = {
        "label": label,
        "exits": [{"direction": d, "lock": lock} for d, lock in exits.items()],
        "items": items,
        "inventory": held,
        "is_exit": False,
    }
    return {"ok": True, "error": None, "data": data}


def test_options_cover_exits_items_and_doors_the_agent_can_open() -> None:
    start = _room("c3", {"north": None, "east": "red", "south": "blue"}, ["red key"], [])
    m = DungeonMap.from_start(json.dumps(start))
    m.apply("move", {"direction": "north"}, _room("e9", {"south": None, "west": None}, [], []))
    assert [o.text for o in options(m)] == [
        "explore e9 west (1 step)",
        "take the red key in c3 (2 steps)",
    ]
    m.inventory = ("red key",)
    m.rooms["c3"].items = []
    (_, unlock) = options(m)  # the blue door has no key yet, so it is not an option
    assert unlock.text == "unlock c3 east with the red key, go through (3 steps)"
    assert unlock.calls == [
        ("move", {"direction": "south"}),
        ("use", {"item": "red key", "direction": "east"}),
        ("move", {"direction": "east"}),
    ]


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_always_the_nearest_option_escapes_every_dev_dungeon(level: str) -> None:
    for seed in DEV_SEEDS:
        row = _play(level, seed, _answers("1")).row
        assert row.success and row.arch_error is None, seed
        assert row.llm_calls <= (row.steps or 0)  # code makes the moves, the model only chooses


def test_an_answer_without_an_option_is_asked_again_at_no_step() -> None:
    seen: list[list[BaseMessage]] = []
    inner = _answers("I am not sure", "99", "1")

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        seen.append(list(messages))
        return inner(messages)

    row = _play("L1", 1000, strategy).row
    plain = _play("L1", 1000, _answers("1")).row
    assert row.success and row.steps == plain.steps and row.llm_calls == plain.llm_calls + 2
    assert "named no option" in str(seen[1][-1].content)
    assert "'99' named no option" in str(seen[2][-1].content)


def test_model_input() -> None:
    seen: list[list[BaseMessage]] = []

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        seen.append(list(messages))
        return AIMessage("1")

    _play("L2", 1001, strategy)
    for messages in seen:
        assert [type(m) for m in messages] == [SystemMessage, HumanMessage]
        assert messages[0].content == BASE_PROMPT + "\n\n" + HYBRID_INSTRUCTIONS
        text = str(messages[1].content)
        assert "Your map (built from your tool results so far):" in text
        assert "\nOptions:\n1. " in text
    assert str(seen[1][1].content).startswith("Last choice: ")
