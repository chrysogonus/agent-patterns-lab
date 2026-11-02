"""The viewer's About card: what an architecture defines on one game, drawn as its graph.

Hand-written, so the diagram can show edges LangGraph cannot infer (plain `str` routers, `Command`
handoffs, `Send`); `tests/viewer/test_about.py` checks every drawn node against the compiled graph,
every role against the nodes, and the tools row against the game's tools. Viewer code: it may read
the architectures' constants, and architectures never import it.
"""

from dataclasses import dataclass, field, replace
from typing import Literal

from apl.arch.hybrid import MAX_MISSES, SIGNAL_PROBES, SIGNAL_SUBMITS
from apl.arch.plan_execute import MAX_IDLE, MAX_SUBGOALS, MAX_TURNS
from apl.arch.reflexion import MAX_STALE
from apl.arch.supervisor import TEAMS
from apl.problems import PROBLEMS
from apl.runner.registry import SUPPORTS


@dataclass(frozen=True, slots=True)
class Node:
    id: str  # the LangGraph node name; "<group>/<name>" inside a subgraph; "end" for the end mark
    label: str
    kind: Literal["model", "code", "end"]
    x: int
    y: int
    w: int = 110
    h: int = 32
    roles: tuple[str, ...] = ()  # first words of the model-call roles that light it; "" is none
    group: str | None = None


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    target: str
    label: str = ""
    bend: int = 0  # control-point offset of a curved edge, to the right of its direction; a
    # loop (source == target) is drawn above its node, or below it when bend < 0


@dataclass(frozen=True, slots=True)
class Group:
    id: str  # the subgraph's node name in the parent graph
    label: str
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True, slots=True)
class About:
    summary: str
    width: int
    height: int
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    groups: tuple[Group, ...] = ()
    facts: tuple[tuple[str, str], ...] = field(default=())


TOOLS = {
    "dungeon": "look, move, take, use",
    "survey": "look, move, submit",
    "signal": "look, probe, submit",
    "rune": "look, move",
    "workshop": "look, inspect, gather, craft",
}

MEMORY = {
    "dungeon": "a room map: every room seen, its exits and where they lead, items, the inventory "
    "and the doors opened",
    "survey": "a field map: a picture of the cells seen and their deposits, the walls seen, and "
    "the unseen cells next to seen ones",
    "signal": "a probe log: the pipe's runs and every probe answer, in order",
    "rune": "a walk log: the floor, the agent's cell, and every walk from the start with how it "
    "ended",
    "workshop": "a workshop log: the goal, the stock, the inventory and every recipe inspected",
}

ENDS = {
    "dungeon": "the exit is reached or the step budget runs out",
    "survey": "a total is submitted or the step budget runs out",
    "signal": "a segment is submitted or the step budget runs out",
    "rune": "the goal is reached or the step budget runs out",
    "workshop": "the goal is crafted, the goal can no longer be made, or the step budget runs out",
}

FAILS = {  # A4: what ends an attempt, besides giving up or going stale
    "dungeon": "there is no wrong answer to fail on",
    "survey": "a wrong total is submitted",
    "signal": "a wrong segment is submitted",
    "rune": "a step springs a trap (the reply's later moves don't run)",
    "workshop": "the goal can no longer be made (the reply's later calls don't run)",
}

STALE = {  # A4's "nothing new"
    "dungeon": "no new room",
    "survey": "no new cell",
    "signal": "no newly probed segment",
    "rune": "no cell new to this attempt",
    "workshop": "no progress in the workshop log",
}

OFFERS = {  # A6's option list
    "dungeon": "every unexplored exit, every locked door it holds the key for, and every known "
    "item, each with the shortest known route, which code walks; fewest steps first",
    "signal": f"the {SIGNAL_PROBES} probes that split the remaining suspects most evenly, with "
    f"how many suspects each answer leaves; submissions once {SIGNAL_SUBMITS} or fewer are left",
    "rune": "every move that stays on the floor, with what happened on that tile before (safe or "
    "a trap, at which walk step); it never guesses the rule",
    "workshop": "every action possible now: inspect a named item, gather a raw material in stock, "
    "or craft with a recipe whose inputs are held; it never compares recipes",
}


def _loop(arch: str, problem: str) -> About:
    react = arch == "react"
    tools = "tools" if react else "act"
    facts = [
        (
            "Model sees",
            "the whole conversation so far: every reply and tool result"
            if react
            else "its last reply with that reply's tool results, then the memory",
        ),
        ("Memory", "none beyond the conversation" if react else MEMORY[problem]),
        ("Tools", f"agent: {TOOLS[problem]}"),
        ("Ends when", f"{ENDS[problem]}, or the model answers without a tool call"),
    ]
    if arch == "mapstate_routes":
        facts.append(
            ("Planning aid", "under the map, each unexplored exit with the moves that reach it")
        )
    summary = {
        "react": "The baseline: the model calls tools in a loop and remembers only the chat.",
        "mapstate": "The same loop, but the chat history is replaced by a memory that code "
        "rebuilds from tool results every turn.",
        "mapstate_routes": "A2 with one planning aid: the known route to each unexplored exit.",
    }[arch]
    return About(
        summary,
        420,
        130,
        (
            Node("agent", "agent", "model", 30, 30, roles=("",)),
            Node(tools, tools, "code", 280, 30),
            Node("end", "end", "end", 65, 96, 40, 22),
        ),
        (
            Edge("agent", tools, "tool calls", 14),
            Edge(tools, "agent", "results" if react else "results → memory", 14),
            Edge("agent", "end", "no tool call"),
        ),
        facts=tuple(facts),
    )


def _plan_execute(problem: str) -> About:
    return About(
        "A planner writes subgoals, an executor carries them out in order, and a replanner steps "
        "in only when a subgoal fails or the plan runs out.",
        460,
        250,
        (
            Node("planner", "planner", "model", 10, 20, roles=("planner",)),
            Node("replanner", "replanner", "model", 290, 20, roles=("replanner",)),
            Node("executor", "executor", "model", 10, 175, roles=("executor",)),
            Node("act", "act", "code", 290, 175),
            Node("end", "end", "end", 410, 100, 40, 22),
        ),
        (
            Edge("planner", "executor", "first subgoal"),
            Edge("executor", "act", "tool calls", 14),
            Edge("act", "executor", "results", 14),
            Edge("executor", "executor", "done: next subgoal", -1),
            Edge("executor", "replanner", "Cannot: / plan used up", 26),
            Edge("replanner", "executor", "new plan", 26),
            Edge("act", "replanner", f"{MAX_TURNS} turns"),
            Edge("replanner", "end", "done"),
        ),
        facts=(
            (
                "Model sees",
                "planner and replanner: the start, the reports so far, the plan still to do, the "
                "steps used and the memory; executor: its subgoal, its last turn and the memory",
            ),
            ("Memory", MEMORY[problem]),
            ("Tools", f"executor: {TOOLS[problem]}; planner and replanner: none"),
            (
                "Replans when",
                f'a subgoal is reported with "Cannot:", runs {MAX_TURNS} turns without '
                "finishing, or the plan is used up; a done subgoal hands straight to the next",
            ),
            (
                "Ends when",
                f"{ENDS[problem]}, the replanner answers done, {MAX_IDLE} subgoals in a row make "
                f"no tool call, or {MAX_MISSES} plans in a row are unusable",
            ),
            ("Limits", f"up to {MAX_SUBGOALS} subgoals per plan"),
        ),
    )


def _reflexion(problem: str) -> About:
    attempts = PROBLEMS[problem].max_attempts
    kept = "kept across attempts" if problem == "rune" else "cleared at each restart"
    return About(
        "A2 that tries again: after a failed attempt a reflector writes a note, the world "
        "restarts, and the next attempt sees the notes.",
        520,
        200,
        (
            Node("actor", "actor", "model", 10, 40, roles=("actor",)),
            Node("act", "act", "code", 195, 40),
            Node("reflector", "reflector", "model", 400, 40, roles=("reflector",)),
            Node("restart", "restart", "code", 400, 150),
            Node("end", "end", "end", 230, 165, 40, 22),
        ),
        (
            Edge("actor", "act", "tool calls", 14),
            Edge("act", "actor", "results", 14),
            Edge("act", "reflector", "attempt failed"),
            Edge("actor", "reflector", "gave up", -48),
            Edge("reflector", "restart", "note"),
            Edge("restart", "actor", "next attempt"),
            Edge("restart", "end", "no attempt left"),
        ),
        facts=(
            (
                "Model sees",
                "actor: the attempt number, the notes so far, its last turn and the memory; "
                "reflector: why the attempt ended, its last reply, the memory and the notes",
            ),
            ("Memory", f"{MEMORY[problem]}; {kept}"),
            ("Tools", f"actor: {TOOLS[problem]}; reflector: none"),
            (
                "Attempt fails when",
                f"{FAILS[problem]}; the actor gives up; or {MAX_STALE} turns in a row bring "
                f"{STALE[problem]}",
            ),
            ("Attempts", f"up to {attempts}, sharing one step budget"),
            ("Ends when", f"{ENDS[problem]}, or the last attempt fails"),
        ),
    )


def _supervisor(problem: str) -> About:
    team = TEAMS[problem]
    (first, own1), (second, own2) = team.tools.items()
    groups = (
        Group(first, f"{first} · {', '.join(own1)}", 10, 118, 210, 92),
        Group(second, f"{second} · {', '.join(own2)}", 240, 118, 210, 92),
    )
    nodes = [Node("supervisor", "supervisor", "model", 165, 15, 130, roles=("supervisor",))]
    edges = [Edge("supervisor", "end", "done")]
    for g in groups:
        helper, act = f"{g.id}/helper", f"{g.id}/act"
        nodes += [
            Node(helper, "helper", "model", g.x + 12, 162, 92, roles=(g.id,), group=g.id),
            Node(act, "act", "code", g.x + 120, 162, 78, group=g.id),
        ]
        edges += [
            Edge("supervisor", helper, "task", 24),
            Edge(helper, "supervisor", "report", 24),
            Edge(helper, act, "", 10),
            Edge(act, helper, "", 10),
        ]
    nodes.append(Node("end", "end", "end", 340, 20, 40, 22))
    tools = f"{first}: {', '.join(own1)}; {second}: {', '.join(own2)}; supervisor: none"
    return About(
        "A supervisor hands one task at a time to one of two helpers, each holding half the tools.",
        460,
        222,
        tuple(nodes),
        tuple(edges),
        groups,
        (
            (
                "Model sees",
                "supervisor: the start, the handoffs so far, the steps used and the memory; "
                "helpers: their task, their last turn and the memory",
            ),
            ("Memory", f"{MEMORY[problem]}; shared by both helpers"),
            ("Tools", f"{tools}; a call to the other helper's tool is refused and costs no step"),
            (
                "Ends when",
                f"{ENDS[problem]}, the supervisor answers done, {MAX_IDLE} handoffs in a row make "
                f"no tool call, or {MAX_MISSES} answers in a row are unusable",
            ),
            ("Limits", f"{MAX_TURNS} turns per task"),
        ),
    )


def _hybrid(problem: str) -> About:
    return About(
        "Code lists the options, the model answers with a number, and code makes the calls.",
        480,
        150,
        (
            Node("plan", "plan", "code", 10, 50, 110, 34),
            Node("choose", "choose", "model", 185, 50, 110, 34, roles=("",)),
            Node("act", "act", "code", 360, 50, 110, 34),
            Node("end", "end", "end", 45, 115, 40, 22),
        ),
        (
            Edge("plan", "choose", "options"),
            Edge("choose", "act", "a number"),
            Edge("act", "plan", "memory updated", -46),
            Edge("choose", "choose", "not a number: ask again"),
            Edge("plan", "end", "no option left"),
        ),
        facts=(
            ("Model sees", "the memory and a numbered option list; it answers with one number"),
            ("Memory", MEMORY[problem]),
            ("Tools", "none for the model: code makes every call, and each costs a step"),
            ("Code offers", OFFERS[problem]),
            (
                "Ends when",
                f"{ENDS[problem]}, no option is left, or {MAX_MISSES} answers in a row name no "
                "option (asking again costs no step)",
            ),
        ),
    )


def _scouts(arch: str, problem: str) -> About:
    survey = problem == "survey"
    lead = "orchestrate" if arch == "fanout" else "plan"
    nodes = [
        Node("scout", "scout ×N", "model", 60, 100, roles=("scout",)),
        Node("act", "act", "code", 280, 100),
    ]
    edges = [Edge("scout", "act", "tool calls", 14), Edge("act", "scout", "next turn", 14)]
    if arch == "blackboard":
        nodes = [replace(n, y=40) for n in nodes] + [Node("end", "end", "end", 305, 110, 40, 22)]
        edges.append(Edge("act", "end", "all done"))
        summary = (
            "No planner: scouts take turns one at a time on one live board and claim frontiers."
        )
        how = "one scout moves at a time, sees every scout's results and claims a frontier"
        who = "any scout, when the board shows every cell"
        height = 150
    elif arch == "fanout":
        nodes.append(Node(lead, lead, "model", 170, 15, roles=("orchestrator",)))
        edges.append(Edge(lead, "scout", "once: tasks, step limits"))
        if survey:
            nodes += [
                Node("collect", "collect", "model", 280, 170, roles=("orchestrator",)),
                Node("end", "end", "end", 315, 225, 40, 22),
            ]
            edges += [Edge("act", "collect", "all done"), Edge("collect", "end", "total")]
        else:
            nodes.append(Node("end", "end", "end", 305, 170, 40, 22))
            edges.append(Edge("act", "end", "all done"))
        summary = "An orchestrator splits the work once; scouts explore on their own maps."
        how = (
            "decided once: up to 4 scouts with a task and a step limit each; they never hear "
            "from each other"
        )
        who = "the orchestrator, from the scouts' reports (collect)"
        height = 255 if survey else 210
    else:
        nodes += [
            Node(lead, lead, "model", 170, 15, roles=("orchestrator",)),
            Node("end", "end", "end", 330, 20, 40, 22),
        ]
        edges += [
            Edge(lead, "scout", "tasks this round", -14),
            Edge("act", lead, "round over", -14),
            Edge(lead, "end", "total" if survey else "done"),
        ]
        summary = (
            "An orchestrator hands out short tasks each round and replans on the map merged "
            "from every scout."
        )
        how = (
            "each round the orchestrator reads the merged map and gives some scouts a short "
            "task with a step limit"
        )
        who = "the orchestrator, by answering with the total"
        height = 210
    facts = [
        (
            "Model sees",
            "each scout: its task, its last turn and its map"
            + ("" if arch == "blackboard" else "; the orchestrator plans without tools"),
        ),
        (
            "Memory",
            f"{'each scout its own' if arch == 'fanout' else 'one shared'} "
            f"{MEMORY[problem].split(':')[0]}",
        ),
        ("Tools", f"each scout: {TOOLS[problem]}"),
        ("Coordination", how),
        ("Ends when", f"{ENDS[problem]}, or every scout is done"),
    ]
    if survey:
        facts.append(("Who submits", who))
    return About(summary, 460, height, tuple(nodes), tuple(edges), facts=tuple(facts))


def about(arch: str, problem: str) -> About | None:
    """The card for `arch` on `problem`, or None for an architecture without one."""
    if problem not in SUPPORTS.get(arch, ()):
        return None
    if arch in ("react", "mapstate", "mapstate_routes"):
        return _loop(arch, problem)
    if arch == "plan_execute":
        return _plan_execute(problem)
    if arch == "reflexion":
        return _reflexion(problem)
    if arch == "supervisor":
        return _supervisor(problem)
    if arch == "hybrid":
        return _hybrid(problem)
    return _scouts(arch, problem)
