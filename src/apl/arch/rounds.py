"""A8 supervisor in rounds: the orchestrator hands out short tasks and replans on the merged map.

Each round the orchestrator sees what all scouts have seen; the scouts it gives a task see the
merged map of the round's start plus their own results (specs/004 contracts/orchestrators.md).
On the survey field the stop answer is the total, which the graph submits (specs/005 R14).
Written by the agent at the experimenter's request.
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from apl.arch.hybrid import MAX_MISSES
from apl.arch.scouts import (
    ScoutGraph,
    ScoutTurn,
    SharedMap,
    act,
    dispatch,
    first_scout,
    new_scout,
    read_answer,
    read_tasks,
    read_total,
    round_view,
    scout_node,
    submit,
)
from apl.kit import Kit

# Explains the setup and the answer format only; no advice on how to lead the scouts.
ROUNDS_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. You lead up to 4 scouts, numbered 0 to 3. \
Scout 0 is in the start room; another scout appears there when you first give it a task. Each \
round you see the map merged from all scouts' tool results, where each scout is and what it \
holds, and how the last round went. You give some scouts a short task with a step limit; they \
carry out their tasks at the same time, and then you plan the next round. Keys stay with the \
scout that took them. Every tool call of every scout costs a step from the one shared budget. \
Answer with one JSON object and nothing else:
{"tasks": [{"scout": <0 to 3>, "task": "<what to do>", "steps": <step limit>}, ...]}
or {"done": true} to stop."""

# The same for the survey field: the stop answer is the total (specs/005 contracts).
FIELD_ROUNDS_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. You lead up to 4 scouts, numbered 0 to 3. \
Scout 0 is in A1; another scout appears there when you first give it a task. Each round you see \
the map merged from all scouts' tool results, where each scout is, and how the last round went. \
You give some scouts a short task with a step limit; they carry out their tasks at the same \
time, and then you plan the next round. Every tool call of every scout costs a step from the one \
shared budget. Answer with one JSON object and nothing else:
{"tasks": [{"scout": <0 to 3>, "task": "<what to do>", "steps": <step limit>}, ...]}
or {"total": <the number of deposits in the whole field>} to submit it and end."""


class RoundsState(ScoutGraph):
    note: str  # how the last round went, or why the last answer was not used
    misses: int
    finished: bool


def play(kit: Kit) -> None:
    survey = kit.problem == "survey"
    instructions = FIELD_ROUNDS_INSTRUCTIONS if survey else ROUNDS_INSTRUCTIONS
    system = SystemMessage(kit.base_prompt + "\n\n" + instructions)
    board = SharedMap.from_start(kit.start, 0)
    everyone = [first_scout(kit, lambda number, start: board)]

    def plan(state: RoundsState) -> dict[str, Any]:
        report = []
        for s in state["scouts"]:
            report.append(
                f"scout {s.number}: "
                + (f"finished: {s.report}" if s.report else "used up its steps")
            )
            if s.failed:
                report.append(f"scout {s.number}: last failed call: {s.failed}")
        last = "Last round:\n" + "\n".join(report) if report else "This is the first round."
        prompt = (
            f"{state['note']}\n\n{board.render(None)}\n\n"
            f"Steps used so far: {state['steps']}\n\n{last}"
        ).lstrip()
        config: Any = {"metadata": {"role": "orchestrator"}}
        reply = kit.model.invoke([system, HumanMessage(prompt)], config=config)
        assert isinstance(reply, AIMessage)
        answer = read_answer(str(reply.text))
        if survey and isinstance(answer, dict) and "total" in answer:
            total = read_total(answer)
            if isinstance(total, str):
                answer = total
            else:
                submit(kit, total)  # ends the episode: the tool node raises EpisodeEnded
                return {"scouts": [], "finished": True}
        elif not survey and isinstance(answer, dict) and answer.get("done") is True:
            return {"scouts": [], "finished": True}
        tasks = read_tasks(answer, "tasks", with_scout=True) if isinstance(answer, dict) else answer
        if isinstance(tasks, str):
            note = f"Your answer was not used: {tasks}. Answer with one JSON object as described."
            return {"scouts": [], "note": note, "misses": state["misses"] + 1}
        dropped = []
        for number, _, _ in sorted(tasks, key=lambda t: t[0] or 0):
            while number is not None and number >= len(everyone):
                scout = new_scout(kit, lambda n, start: board)
                if scout is None:
                    dropped.append(number)
                    break
                board.add(scout.number)
                everyone.append(scout)
        tasked = []
        for number, task, steps in tasks:
            if number in dropped or number is None:
                continue
            scout = everyone[number]
            scout.task, scout.steps_left, scout.done, scout.report = task, steps, False, ""
            scout.failed = ""
            scout.last_turn = []
            scout.view = round_view(board)
            tasked.append(scout)
        note = f"No scout could be added for: {dropped}." if dropped else ""
        return {"scouts": tasked, "note": note, "misses": 0}

    def after_plan(state: RoundsState) -> Any:
        if state["finished"] or state["misses"] >= MAX_MISSES:
            return END
        return dispatch(kit, "plan")(state) if state["scouts"] else "plan"

    graph = StateGraph(RoundsState)
    graph.add_node("plan", plan)
    graph.add_node("scout", scout_node(kit), input_schema=ScoutTurn)
    graph.add_node("act", act)
    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", after_plan, ["plan", "scout", END])
    graph.add_edge("scout", "act")
    graph.add_conditional_edges("act", dispatch(kit, "plan"), ["scout", "plan"])
    graph.compile().invoke(
        {
            "scouts": [],
            "replies": [],
            "board": board,
            "steps": 0,
            "note": "",
            "misses": 0,
            "finished": False,
        },
        config={"recursion_limit": kit.recursion_limit},
    )
