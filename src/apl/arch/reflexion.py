"""A4 Reflexion: an attempt, a note on what went wrong, and another attempt from the start.

The actor plays each attempt as A2 plays an episode, with a map built from that attempt's tool
results and the notes from earlier attempts. After a failed attempt the reflector writes a note
and the world is restarted; every attempt's steps count toward the one budget (specs/007
contracts/reflexion.md, constitution 2.1.0). Written by the agent at the experimenter's request.
"""

import json
from typing import Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from apl.arch.dungeon_map import DungeonMap
from apl.arch.field_map import FieldMap
from apl.arch.mapstate import FIELD_MAP_INSTRUCTIONS, MAP_INSTRUCTIONS
from apl.kit import Kit

# Actor turns in a row that add no room or cell to the map; then the attempt has failed. A
# constant, not derived from the budget, which would reveal the optimum (research R5).
MAX_STALE = 12

# Explain attempts, notes and the job; no advice about the dungeon or the field (research R6).
ACTOR_INSTRUCTIONS = """\
You may get up to {max_attempts} attempts. An attempt fails when you answer without a tool call, \
when many turns in a row show you nothing new, or, if the task ends with a submission, when the \
submitted answer is wrong. After a failed attempt everything is put back as it was at the start, \
your map is cleared, and you start again; the steps of every attempt count toward the one budget. \
Notes you wrote after earlier attempts are shown under "Notes from earlier attempts:"."""

REFLECTOR_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. An attempt has just failed. You see why it \
ended, its last reply, the map it built and the notes from earlier attempts. Write a short note \
for the next attempt, which starts again from the start with an empty map and sees only the \
notes. Answer with the note only."""

WRONG_TOTAL = "wrong total"


class ReflexionState(TypedDict):
    # No reducers: each write replaces the value, as in A2 (data-model.md).
    messages: list[BaseMessage]  # the actor's latest turn only
    map: DungeonMap | FieldMap  # this attempt's
    notes: list[str]
    attempt: int
    stale: int  # actor turns in a row that added nothing to the map
    started: bool  # whether this attempt has shown the start result
    failure: str  # why the attempt ended; "" while it goes on
    last_reply: str


def _has_calls(message: BaseMessage) -> bool:
    # Unparsable calls go to the tools too: they cost a step and get an error back.
    return isinstance(message, AIMessage) and bool(message.tool_calls or message.invalid_tool_calls)


def _until_submit(message: BaseMessage) -> AIMessage:
    """The reply with its calls up to the first submit: a submission ends the attempt either way,
    and later calls would run in a restarted world that this attempt's map does not show."""
    assert isinstance(message, AIMessage)
    names = [c["name"] for c in message.tool_calls]
    if "submit" not in names[:-1]:
        return message
    kept = message.tool_calls[: names.index("submit") + 1]
    return message.model_copy(update={"tool_calls": kept, "invalid_tool_calls": []})


def _size(found: DungeonMap | FieldMap) -> int:
    return len(found.rooms) if isinstance(found, DungeonMap) else len(found.cells)


def _notes(notes: list[str]) -> str:
    if not notes:
        return ""
    return "Notes from earlier attempts:\n" + "\n".join(f"{i}. {n}" for i, n in enumerate(notes, 1))


def play(kit: Kit) -> None:
    model = kit.model.bind_tools(kit.tools)
    survey = kit.problem == "survey"
    map_instructions = FIELD_MAP_INSTRUCTIONS if survey else MAP_INSTRUCTIONS
    actor_text = ACTOR_INSTRUCTIONS.format(max_attempts=kit.max_attempts)
    actor_system = SystemMessage(kit.base_prompt + "\n\n" + map_instructions + " " + actor_text)
    reflector_system = SystemMessage(kit.base_prompt + "\n\n" + REFLECTOR_INSTRUCTIONS)

    def new_map() -> DungeonMap | FieldMap:
        # A restarted world looks exactly like the start (research R5).
        return FieldMap.from_start(kit.start) if survey else DungeonMap.from_start(kit.start)

    def render(found: DungeonMap | FieldMap) -> str:
        return found.render(False) if isinstance(found, DungeonMap) else found.render()

    def actor(state: ReflexionState) -> dict[str, Any]:
        head = "\n\n".join(
            part
            for part in [
                f"Attempt {state['attempt']} of {kit.max_attempts}.",
                _notes(state["notes"]),
                "" if state["started"] else kit.start,
            ]
            if part
        )
        messages = [
            actor_system,
            HumanMessage(head),
            *state["messages"],
            HumanMessage(render(state["map"])),
        ]
        reply = model.invoke(
            messages, config={"metadata": {"role": f"actor (attempt {state['attempt']})"}}
        )
        update: dict[str, Any] = {
            "messages": [reply],
            "started": True,
            "last_reply": str(reply.text),
        }
        if not _has_calls(reply):
            update["failure"] = "gave up"
        return update

    def act(state: ReflexionState) -> dict[str, Any]:
        reply = _until_submit(state["messages"][-1])
        before = _size(state["map"])
        results = kit.tool_node({"messages": [reply]})["messages"]
        calls = {c["id"]: c for c in [*reply.tool_calls, *reply.invalid_tool_calls]}
        wrong = False
        for result in results:
            call = calls[result.tool_call_id]
            args = call["args"] if isinstance(call["args"], dict) else {}
            data = json.loads(str(result.content))
            state["map"].apply(call["name"] or "", args, data)
            found = data.get("data")
            wrong = wrong or (isinstance(found, dict) and found.get("correct") is False)
        stale = 0 if _size(state["map"]) > before else state["stale"] + 1
        failure = WRONG_TOTAL if wrong else ""
        if not failure and stale >= MAX_STALE:
            failure = f"nothing new for {MAX_STALE} turns"
        return {
            "messages": [reply, *results],
            "map": state["map"],
            "stale": stale,
            "failure": failure,
        }

    def reflector(state: ReflexionState) -> dict[str, Any]:
        parts = [
            _notes(state["notes"]),
            f"The attempt ended: {state['failure']}.",
            f"Its last reply: {state['last_reply'] or '(no text)'}",
            render(state["map"]),
        ]
        prompt = HumanMessage("\n\n".join(part for part in parts if part))
        reply = kit.model.invoke(
            [reflector_system, prompt], config={"metadata": {"role": "reflector"}}
        )
        note = str(reply.text).strip()
        return {"notes": [*state["notes"], note] if note else state["notes"]}

    def restart(state: ReflexionState) -> dict[str, Any]:
        # After a wrong total the field has already been restarted (research R3).
        if state["failure"] != WRONG_TOTAL and not kit.restart():
            return {"failure": "no attempt left"}
        return {
            "messages": [],
            "map": new_map(),
            "attempt": state["attempt"] + 1,
            "stale": 0,
            "started": False,
            "failure": "",
        }

    def end_attempt(state: ReflexionState) -> str:
        return "reflector" if state["attempt"] < kit.max_attempts else END

    def after_actor(state: ReflexionState) -> str:
        return "act" if _has_calls(state["messages"][-1]) else end_attempt(state)

    def after_act(state: ReflexionState) -> str:
        return end_attempt(state) if state["failure"] else "actor"

    def after_restart(state: ReflexionState) -> str:
        return END if state["failure"] else "actor"

    graph = StateGraph(ReflexionState)
    graph.add_node("actor", actor)
    graph.add_node("act", act)
    graph.add_node("reflector", reflector)
    graph.add_node("restart", restart)
    graph.add_edge(START, "actor")
    graph.add_conditional_edges("actor", after_actor, ["act", "reflector", END])
    graph.add_conditional_edges("act", after_act, ["actor", "reflector", END])
    graph.add_edge("reflector", "restart")
    graph.add_conditional_edges("restart", after_restart, ["actor", END])
    graph.compile().invoke(
        {
            "messages": [],
            "map": new_map(),
            "notes": [],
            "attempt": 1,
            "stale": 0,
            "started": False,
            "failure": "",
            "last_reply": "",
        },
        config={"recursion_limit": kit.recursion_limit},
    )
