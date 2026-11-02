"""The workshop log: the memory of A2–A5 on the workshop (specs/011 contracts/architectures.md)."""

import json
from collections.abc import Mapping

from apl.arch.workshop_log import WorkshopLog
from apl.workshop import DEV_SEEDS, AgentTools, generate, start_episode
from apl.workshop.plans import greedy_calls
from tests.workshop.lantern import call, lantern


def _log() -> tuple[WorkshopLog, AgentTools]:
    tools = AgentTools(start_episode(lantern()))
    return WorkshopLog.from_start(json.dumps(tools.start.to_dict())), tools


def _use(tools: AgentTools, name: str, args: Mapping[str, object]) -> dict[str, object]:
    if name == "inspect":
        return tools.inspect(args["item"]).to_dict()
    return tools.gather(args["item"]).to_dict()


def test_the_render_at_the_start_and_after_some_calls() -> None:
    log, tools = _log()
    assert log.render() == (
        "Goal: lantern.\n"
        "Stock: coal 1, iron ore 2, resin 1, sand 2, seeds 1, wood 1.\n"
        "Inventory: empty.\n"
        "Recipes seen: none."
    )
    log.apply("inspect", {"item": "lantern"}, tools.inspect("lantern").to_dict())
    log.apply("inspect", {"item": "frame"}, tools.inspect("frame").to_dict())
    log.apply("inspect", {"item": "coal"}, tools.inspect("coal").to_dict())
    log.apply("gather", {"item": "sand"}, tools.gather("sand").to_dict())
    assert log.render() == (
        "Goal: lantern.\n"
        "Stock: coal 1, iron ore 2, resin 1, sand 1, seeds 1, wood 1.\n"
        "Inventory: sand 1.\n"
        "Recipes seen (3):\n"
        "- lantern: frame, lens, oil\n"
        "- frame: recipe 1: iron bar; recipe 2: wood, resin\n"
        "- coal: raw material"
    )
    assert log.known == 3


def test_failed_calls_change_nothing() -> None:
    log, tools = _log()
    before = log.render()
    log.apply("gather", {"item": "frame"}, tools.gather("frame").to_dict())
    log.apply("inspect", {"item": "nails"}, tools.inspect("nails").to_dict())
    assert log.render() == before and log.known == 0


def test_options_follow_what_is_known_and_held() -> None:
    log, tools = _log()
    assert log.options() == [
        ("inspect lantern", ("inspect", {"item": "lantern"})),
        ("gather coal (1 left)", ("gather", {"item": "coal"})),
        ("gather iron ore (2 left)", ("gather", {"item": "iron ore"})),
        ("gather resin (1 left)", ("gather", {"item": "resin"})),
        ("gather sand (2 left)", ("gather", {"item": "sand"})),
        ("gather seeds (1 left)", ("gather", {"item": "seeds"})),
        ("gather wood (1 left)", ("gather", {"item": "wood"})),
    ]
    for name, args in [
        ("inspect", {"item": "lantern"}), ("inspect", {"item": "frame"}),
        ("gather", {"item": "wood"}), ("gather", {"item": "resin"}),
    ]:  # fmt: skip
        log.apply(name, args, _use(tools, name, args))
    texts = [text for text, _ in log.options()]
    assert texts[:4] == ["inspect lens", "inspect oil", "inspect iron bar", "gather coal (1 left)"]
    assert "gather wood (0 left)" not in texts and "gather resin (0 left)" not in texts
    assert texts[-1] == "craft frame with recipe 2 (uses wood, resin)"
    assert log.options()[-1][1] == ("craft", {"item": "frame", "recipe": 2})


def test_the_log_agrees_with_episodes_on_every_w2_dev_seed() -> None:
    for seed in DEV_SEEDS:
        w = generate("W2", seed)
        episode = start_episode(w)
        tools = AgentTools(episode)
        log = WorkshopLog.from_start(json.dumps(tools.start.to_dict()))
        for name, args in greedy_calls(w):
            if episode.end_reason is not None:
                break
            log.apply(name, args, call(episode, name, args).to_dict())
        assert log.stock == episode.stock and log.inventory == episode.inventory
