"""The viewer's About card: what each architecture defines on each game, checked against code."""

from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from apl.problems import PROBLEMS
from apl.runner import registry
from apl.runner.settings import Settings
from apl.viewer.about import about
from tests.runner.scripted import scripted_factory

PAIRS = sorted((arch, game) for arch, games in registry.SUPPORTS.items() for game in games)

# The first word of every metadata role each architecture's model calls carry; "" is no role.
ROLES = {
    "react": {""},
    "mapstate": {""},
    "mapstate_routes": {""},
    "hybrid": {""},
    "plan_execute": {"planner", "executor", "replanner"},
    "reflexion": {"actor", "reflector"},
    "supervisor": {"supervisor", "navigator", "inventory", "researcher", "crafter"},
    "fanout": {"orchestrator", "scout"},
    "rounds": {"orchestrator", "scout"},
    "blackboard": {"scout"},
}


class _Stop(Exception):
    pass


def _kit(problem: str) -> Any:
    p = PROBLEMS[problem]
    episode = p.start_episode(p.generate(sorted(p.levels)[0], 1000))
    return p.build_kit(episode, scripted_factory(lambda m: AIMessage("x"))(Settings(), []))


def _compiled_nodes(arch: str, problem: str, monkeypatch: pytest.MonkeyPatch) -> set[str]:
    """The node names of every graph the architecture compiles, without running it."""
    seen: set[str] = set()
    compile_graph = StateGraph.compile

    def record(self: StateGraph[Any], *args: Any, **kwargs: Any) -> Any:
        seen.update(self.nodes)
        return compile_graph(self, *args, **kwargs)

    def stop(self: Any, *args: Any, **kwargs: Any) -> Any:
        raise _Stop

    monkeypatch.setattr(StateGraph, "compile", record)
    monkeypatch.setattr(CompiledStateGraph, "invoke", stop)
    with pytest.raises(_Stop):
        registry.load(arch)(_kit(problem))
    return seen


@pytest.mark.parametrize(("arch", "problem"), PAIRS)
def test_every_architecture_has_a_card_on_every_game_it_plays(arch: str, problem: str) -> None:
    card = about(arch, problem)
    assert card is not None and card.summary
    ids = {n.id for n in card.nodes}
    assert {e.source for e in card.edges} | {e.target for e in card.edges} <= ids
    assert {n.group for n in card.nodes if n.group} <= {g.id for g in card.groups}
    labels = [label for label, _ in card.facts]
    assert {"Model sees", "Memory", "Tools", "Ends when"} <= set(labels)


@pytest.mark.parametrize(("arch", "problem"), PAIRS)
def test_the_card_draws_the_graphs_real_nodes(
    arch: str, problem: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = about(arch, problem)
    assert card is not None
    drawn = {n.id.split("/")[-1] for n in card.nodes if n.kind != "end"}
    assert drawn | {g.id for g in card.groups} == _compiled_nodes(arch, problem, monkeypatch)


@pytest.mark.parametrize(("arch", "problem"), PAIRS)
def test_every_role_lights_a_node(arch: str, problem: str) -> None:
    card = about(arch, problem)
    assert card is not None
    lit = {role for n in card.nodes for role in n.roles}
    team = {"navigator", "inventory"} if problem == "dungeon" else {"researcher", "crafter"}
    expected = ROLES[arch] - ({"navigator", "inventory", "researcher", "crafter"} - team)
    assert expected <= lit


@pytest.mark.parametrize(("arch", "problem"), PAIRS)
def test_the_tools_row_names_the_games_tools(arch: str, problem: str) -> None:
    card = about(arch, problem)
    assert card is not None
    tools = dict(card.facts)["Tools"]
    names = [t["function"]["name"] for t in _kit(problem).tools]
    if arch == "hybrid":
        assert "code makes" in tools
    else:
        assert all(name in tools for name in names)


def _facts(arch: str, problem: str) -> str:
    card = about(arch, problem)
    assert card is not None
    return " ".join(f"{label}: {text}" for label, text in card.facts)


def test_the_cards_carry_each_games_specifics() -> None:
    rune = _facts("reflexion", "rune")
    assert "trap" in rune and "kept across attempts" in rune
    dungeon = _facts("reflexion", "dungeon")
    assert "gives up" in dungeon and "no wrong answer" in dungeon
    assert "suspects" in _facts("hybrid", "signal")
    assert "never guesses the rule" in _facts("hybrid", "rune")
    workshop = about("supervisor", "workshop")
    assert workshop is not None and {g.id for g in workshop.groups} == {"researcher", "crafter"}
    assert "Cannot:" in _facts("plan_execute", "workshop")
    survey = about("fanout", "survey")
    assert survey is not None and "collect" in {n.id for n in survey.nodes}
    assert "Who submits" in dict(survey.facts)


def test_unknown_architectures_have_no_card() -> None:
    assert about("scripted", "dungeon") is None
