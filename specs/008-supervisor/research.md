# Research: A5 Supervisor

## R1. Graph shape: handoffs and subgraphs

**Decision**: The parent graph has three nodes: `supervisor`, `navigator` and `inventory`. The
supervisor node returns `Command(goto="navigator" | "inventory" | "supervisor" | END,
update=...)`: a handoff is a goto with the task in the update, and an unusable answer goes back
to the supervisor with a note. Each helper is a compiled `StateGraph` (`helper` → `act` → `helper`
…) added as a node, sharing the parent's state schema; a conditional edge after each helper goes
back to the supervisor, or to END after too many idle handoffs.

**Rationale**: plan.md §4 names "subgraphs, handoffs" as the LangGraph features A5 is for. A
compiled subgraph sharing the parent's keys needs no input or output mapping. A probe on
LangGraph 1.2 confirmed that a subgraph node runs with its own recursion counter under the
parent's `recursion_limit`, so a helper's 20 turns (41 super-steps) never meet the parent's limit.

**Alternatives considered**: helpers as plain nodes in one graph (as A3's executor): no subgraph,
so not what A5 is meant to show. Tool-call handoffs (the supervisor calls a `transfer_to_…` tool):
would add tools that no other architecture has, so the tool schemas would differ (constitution
I). The prebuilt `langgraph-supervisor` package: the lab builds every graph by hand.

## R2. Tool split and off-role calls

**Decision**: The navigator's model is bound to the `look` and `move` schemas of `kit.tools`, the
inventory helper's to `take` and `use`, both unchanged. Before `act` runs a reply's calls, A5
splits them: a call named after the other helper's tool is not made; A5 answers it with a
`ToolMessage` of its own, `Not made: take is the inventory helper's tool. It cost no step.`, with
status `error`. Every other call (own tools, unknown names, unparsable calls) goes to
`kit.tool_node` in the reply's order and costs a step as for every architecture. The answers are
put back in the order of the calls.

**Rationale**: the experimenter chose the split by tool to test specialisation; letting an
off-role call through would undo it. Binding only the subset makes such calls rare, but a model
can still name a tool it was not offered. The provider needs every call answered, so the call
must get a reply. Answering it without the dungeon reveals nothing and costs no step, which is
fair: the dungeon was not touched. Unknown names still go to the dungeon, so A5 handles them like
everyone else.

**Alternatives considered**: running off-role calls anyway: undoes the split. Counting them as a
step: a step is a dungeon call (constitution III), and this is not one. Dropping the calls from
the reply: the history would no longer show what the model did.

## R3. Memory and the map

**Decision**: One `DungeonMap` (A2's) in the state, built from every tool result that reached the
dungeon, by both helpers; refused calls are not applied. A helper sees the base prompt with A2's
map instructions and its own instructions, a head message `Your task: <task>` (with `kit.start`
on the episode's first helper turn), its previous reply with that reply's tool results, and the
map. `messages` holds the current helper's latest turn only and is emptied at each handoff.

**Rationale**: as A2, A3 and A4, so A5 differs from A2 in the split and handoffs only. One body
means one map: the navigator's room is the inventory helper's room.

## R4. The supervisor's answer and input

**Decision**: one JSON object: `{"to": "navigator", "task": "..."}`, `{"to": "inventory", "task":
"..."}`, or `{"done": true}`; read with `scouts.read_answer`. An answer is unusable when it has no
JSON object, `to` is not one of the two helpers, or `task` is not a non-empty text; A5 asks again
with the note `Your answer was not used: <why>. Answer with one JSON object as described.` The
supervisor's human message holds, in order: the note (if any), `kit.start`, `Handoffs so far:`
with one line per finished handoff (`n. navigator: <task>: done: <report>` or `unfinished after
20 turns: <report>`, or `none`), `Steps used so far: N`, and the map, last.

**Rationale**: the same format and parsing as A3's planner and A7/A8's orchestrator. The map comes
last, as for every map-showing node.

## R5. Limits

**Decision**: A3's constants, imported from `apl.arch.plan_execute`: `MAX_TURNS = 20` helper turns
per handoff (then the task goes back as unfinished); `MAX_IDLE = 3` handoffs in a row without a
call that reached the dungeon (then A5 stops). `MAX_MISSES = 3` unusable supervisor answers in a
row (from `apl.arch.hybrid`, as A3). A turn with only refused calls counts toward `MAX_TURNS` but
does not make the handoff active.

**Rationale**: constants, not derived from the budget (constitution II); equal to A3's so the two
are bounded alike. A helper that only calls the other's tool runs at most 20 turns per handoff
and three such handoffs end the episode, so SC-004 holds.

## R6. Texts

**Decision**: texts that explain the setup and the answer format only.

- `SUPERVISOR_INSTRUCTIONS`: "In this setup you do not call the tools yourself. You direct two
  helpers who act as one body in the dungeon and see the same map as you (the map's "you" is that
  body). The navigator can call look and move. The inventory helper can call take and use. Hand
  one task at a time to one helper; it reports back when the task is done or cannot be done.
  Every tool call of a helper costs a step from the budget. Answer with one JSON object and
  nothing else: {"to": "navigator", "task": "<task>"}, {"to": "inventory", "task": "<task>"}, or
  {"done": true} to stop."
- `NAVIGATOR_INSTRUCTIONS` and `INVENTORY_INSTRUCTIONS` share one template: "In this setup you can
  call only {own}; {other_job} calls {others}. The line starting with "Your task:" says what to do
  now. When the task is done or cannot be done, answer without a tool call and say briefly what
  you did and found."

**Rationale**: as A3 (R2 there): the texts say what each job is and how to answer, not where to go
or when to use a key.

## R7. Runner, meter and comparison

**Decision**: `ARCHITECTURES["supervisor"] = "apl.arch.supervisor"`, `SUPPORTS["supervisor"] =
{"dungeon"}`; `"supervisor"` in `LEAD_ROLES`, so supervisor calls count in `orchestrator_calls`
and the report's "Calls: orch / scouts" column shows them apart; `REFERENCES["supervisor"] =
"mapstate"`. Roles: `supervisor`, `navigator (task n)`, `inventory (task n)`, with n the number of
handoffs so far.

**Rationale**: the same three tables every architecture uses; nothing else in the runner names an
architecture.

## R8. Viewer

**Decision**: no change. The options list comes from `SUPPORTS`, so `supervisor` appears on the
dungeon only, and every model-call card already shows its role.

## R9. Tests

`tests/arch/test_supervisor.py` with a scripted split walk (the navigator answers with text where
the solution's next action is `take` or `use`, the inventory helper where it is `look` or `move`,
and the supervisor hands to whichever owns the next action):

- L1–L3: success with A2's steps and budget; L3 contains an inventory handoff; roles in order;
  supervisor calls counted as lead calls (SC-001–SC-003, US1 1–2).
- Off-role calls: a navigator reply with `take` and `move` runs the move only, the take costs no
  step and gets the refusal text (US1 3); a navigator that only calls `take` ends within the
  limits (SC-004).
- Stops: `{"done": true}` → `stopped`; unusable answers `MAX_MISSES` times; `MAX_IDLE` idle
  handoffs; `MAX_TURNS` turns back to the supervisor as unfinished; no supervisor call after the
  end (US1 4, edge cases).
- Texts: system messages start with the base prompt; helper systems are base + A2's map
  instructions + their own text; each helper is offered only its tools (SC-002).
- Registry refuses the survey field (US3 2).

`tests/viewer/test_supervisor.py`: offered on the dungeon only; a scripted L3 episode through the
viewer shows the roles in order and replays (US2). `tests/runner/test_supervisor_runs.py`: dry
run without a model, continue, report with `mapstate` as reference (US3, SC-006, SC-007).
