# Research: A3 Plan-and-Execute

No open question was left in the Technical Context; these are the design decisions, each checked
against the existing code (`src/apl/arch/mapstate.py`, `rounds.py`, `scouts.py`,
`src/apl/runner/meter.py`, `compare.py`, `spec.py`, `src/apl/viewer/events.py`, `app.py`).

## R1 The graph: four nodes and two cycles

**Decision**: one `StateGraph` with the nodes `planner`, `executor`, `act` and `replanner`:

```text
START → planner ─(usable plan)→ executor ─(tool calls)→ act ─(turns left)→ executor
           │ (unusable, < 3)         │ (no tool call: report)    │ (turn limit)
           └──→ planner              └──→ replanner ←───────────┘
                                         │ (new plan) → executor
                                         │ (unusable, < 3) → replanner
                                         └ (done, or a limit hit) → END
```

The inner cycle (executor ⇄ act) is A2's loop with a subgoal; the outer cycle (executor →
replanner → executor) is the planning loop.

**Rationale**: plan.md names "multiple nodes, cycles" as what A3 teaches. Separate `planner` and
`replanner` nodes keep the two jobs and their prompts apart (spec FR-002) and show up as two roles
in the viewer. `act` stays its own node as in A2, so the map update is plain code between model
turns.

**Alternatives considered**: one `plan` node for both jobs, as A8's orchestrator does: fewer
lines, but the first plan and a revision would share one prompt and one role, and the viewer
could not tell them apart. A subgraph for the executor: it would hide the inner cycle from the
outer graph, and nothing else needs the isolation.

## R2 The executor is A2 with a subgoal line

**Decision**: the executor's messages are A2's turn plus a subgoal line, built like a scout's
(`scouts.scout_messages`): the system message is the base prompt, A2's map instructions
(`MAP_INSTRUCTIONS` or `FIELD_MAP_INSTRUCTIONS`) and `EXECUTOR_INSTRUCTIONS`; then
`Your subgoal: <text>` (with the start result appended on the episode's first executor turn);
then its previous reply with that reply's tool results; then the rendered map. The previous turn
is cleared when a new subgoal starts; the map is one object for the whole episode, updated in
`act` exactly as A2's `act` does.

`EXECUTOR_INSTRUCTIONS` (problem-neutral):

> The line starting with "Your subgoal:" says what to do now; it is one step of a longer plan.
> When the subgoal is done or cannot be done, answer without a tool call and say briefly what you
> did and found.

**Rationale**: spec FR-003 and the comparison reference: A3 must differ from A2 in planning only.
The wording matches the scouts' task instructions, which already ask for a report without a tool
call; it explains the line, not how to explore (FR-006).

**Alternatives considered**: reusing `ScoutState` and `scouts.act` with one scout: A3 would then
be A8 with one scout, its renders would go through `SharedMap`, and its instructions would talk
about other scouts. A ReAct executor: mixes the memory effect into the planning effect (spec
Assumptions).

## R3 Planner and replanner answers are one JSON object

**Decision**:

- Planner: `{"plan": ["<subgoal>", ...]}` with 1 to `MAX_SUBGOALS` = 8 non-empty strings.
- Replanner: `{"plan": [...]}` with the subgoals still to do (the same rules), or
  `{"done": true}` to stop.

Both are read with `scouts.read_answer` (the first `{` to the last `}`), as A7 and A8 do. An
unusable answer is answered on the next call with a note that says why ("Your answer was not
used: …"), as in A8. `MAX_MISSES` = 3 unusable answers in a row (from `apl.arch.hybrid`, shared
by A6–A8) stop A3.

**Rationale**: the orchestrators' format is proven on both models used so far and keeps the
reply parseable by code (constitution IV). A cap of 8 keeps a plan readable and the prompt small;
it is a constant, not derived from the budget.

**Alternatives considered**: structured output (`with_structured_output`): providers differ in
support and it changes the request A3 sends compared with A2's tool-bound calls, which the meter
and transcript treat the same way today. A numbered plain-text list: harder to validate.

## R4 What the planner and replanner see

**Decision**:

- System message: the base prompt and `PLANNER_INSTRUCTIONS` or `REPLANNER_INSTRUCTIONS`.
- Planner input: the start result and the rendered map (the same map the executor sees).
- Replanner input: a note if its last answer was not used; the start result (spec FR-004); the subgoals done so far, each with
  its outcome (`done: <report>` or `unfinished after 20 turns: <last reply text>`); the subgoals
  still planned; `Steps used so far: N`; the rendered map.

The instructions explain the setup and the answer format only (FR-006):

> In this setup you do not call the tools yourself. You write a plan: a short ordered list of
> subgoals. An executor carries them out one at a time with the tools, sees the same map as you
> (the map's "you" is the executor), and reports back after each subgoal. Every tool call of the
> executor costs a step from the budget. Answer with one JSON object and nothing else:
> {"plan": ["<subgoal>", ...]} with 1 to 8 subgoals.

The replanner's text is the same with "After each subgoal you see its report, the map and the
plan so far, and answer with the subgoals still to do: {"plan": [...]}, or {"done": true} to
stop." Both have no problem-specific wording: the base prompt says what the goal is.

**Rationale**: constitution II: everything shown comes from tool results (the map, the reports,
the step count the agent can count itself). A8's orchestrator already sees the steps used.

**Alternatives considered**: giving the planner the message history: the history is what A2
removed, and the map holds the same facts.

## R5 Limits are constants

**Decision**: in `src/apl/arch/plan_execute.py`:

| Constant | Value | Stops |
| --- | --- | --- |
| `MAX_SUBGOALS` | 8 | a plan longer than this is unusable |
| `MAX_TURNS` | 20 | executor turns on one subgoal; then it goes back to the replanner as unfinished |
| `MAX_IDLE` | 3 | subgoals in a row that end without any tool call; then A3 stops |
| `MAX_MISSES` | 3 (imported) | unusable planner or replanner answers in a row; then A3 stops |

**Rationale**: spec FR-007, FR-008, edge cases. None is derived from the budget, which is 6× the
shortest solution on the dungeon and 3× the reference walk on the field and would reveal it
(constitution II, the same reason `RECURSION_LIMIT` is a constant). 20 turns is about the
shortest L3 solution's length on the dev seeds, so one subgoal can still be "walk to the far
side". The token cap and the step budget remain the hard stops.

**Super-steps**: each executor turn costs 2 super-steps (executor, act), each planner call 1.
Within `RECURSION_LIMIT` = 1000 this allows the largest budget (S2/S3, about 300 steps at one call
per turn: about 600) plus a replan every 20 turns (about 15) with room to spare.

**Alternatives considered**: a step limit per subgoal written by the planner, as in A8: it would
make A3 a one-scout A8 and asks a small model for numbers it guesses badly (M4 findings).

## R6 Ending the episode

**Decision**: only the executor calls tools. The episode ends through the kit as for every
architecture: entering the dungeon exit or a successful `submit` makes the tool node raise
`EpisodeEnded`, which the runner catches; the budget does the same. When the replanner answers
`{"done": true}`, or a limit stops A3, `play` returns and the runner records the episode as
`stopped` (given up). On the survey field the executor submits the total itself, as A2 does.

**Rationale**: spec FR-005, FR-007, FR-009. A3 then needs no `submit` helper, unlike A7/A8, and
its survey and dungeon graphs are the same.

**Alternatives considered**: a `{"total": N}` replanner answer that the graph submits, as in A8:
it would add a second way to act on the world and make the survey graph differ from the
dungeon's.

## R7 Roles: planner and replanner count as orchestrator calls

**Decision**: model calls carry the metadata role `planner`, `replanner` or
`executor (subgoal N)`, where N counts the subgoals started in the episode from 1. The meter
counts calls whose role is in `LEAD_ROLES = {"orchestrator", "planner", "replanner"}` into the
existing `orchestrator_calls` field, so the report's "Calls: orch / scouts" column shows A3's
planning calls apart from its executor calls without a new column.

**Rationale**: FR-010, FR-015. The viewer already prints any role on its model-call card
(`index.html` `card(call, role)`) and diffs each call's input against the previous call of the
same role (`events.py`), so a role per subgoal shows the subgoal on its first card in full and
labels every executor card with its subgoal (FR-018). Step frames fall back to the latest call
for roles other than `scout N` (`app.py`), which is the executor's, because A3's calls never
overlap. Rows written before this feature keep their meaning: no existing architecture uses the
new roles.

**Alternatives considered**: a new `planner_calls` field and column: more change in results,
report and tests for the same information. Using the role `orchestrator` for both planning jobs:
the viewer could not tell the first plan from a revision.

## R8 Registry, comparison and the dry-run estimate

**Decision**:

- `registry.ARCHITECTURES["plan_execute"] = "apl.arch.plan_execute"`, `SUPPORTS` both problems.
  The viewer's architecture list (`app.py` `architecture_names`, written modules of the
  registry) and `apl run --arch` follow from it.
- `compare.REFERENCES["plan_execute"] = "mapstate"`.
- The dry-run call estimate stays as it is (one call per budget step plus one, per episode). It
  is already labelled an estimate that does not cover orchestrator calls (`spec.py`); tokens and
  cost stay hard bounds through the token cap. Spec FR-013 and US3 scenario 1 are corrected to
  say this.

**Rationale**: the estimate's bound is the budget, and A3's planning calls are at most about one
per 20 steps plus the misses; an architecture-specific estimate would be new machinery for a
number the token cap already bounds.

**Alternatives considered**: adding `budget / MAX_TURNS + MAX_MISSES` calls for A3: the runner
would have to know an architecture's internals, which nothing else in the runner does.

## R9 Joining the M4 comparison

**Decision**: nothing new is needed. `apl report` takes several run folders and refuses them when
`model`, `temperature`, `reasoning_effort`, `token_cap`, `num_ctx`, `max_output_tokens` or
`prompt_fingerprint` differ (`report.py` `COMPARED`). The dungeon's fingerprint today is
`ff9afb3b9f66`, the same as the M4 run `20261031-221233-…`. So
`apl run --arch plan_execute --level all --seeds dev --limit 1` with the M4 settings, reported
together with the M4 run, adds A3 to its comparison. A test reports a scripted A3 run together
with a scripted run of the other architectures (SC-007).

**Rationale**: FR-016 asks for the capability, not a run; the run is the experimenter's choice.

## R10 Tests

**Decision**: `tests/arch/test_plan_execute.py`, with the scripted model and helpers from
`tests/runner/scripted.py` and `tests/arch/orchestrated.py` (`by_system`, `by_task`-style routing
on the subgoal line, `json_answer`, `walk_solution`, `walk_field`, `recording`, `roles`):

- escape on L1–L3 with a one-subgoal plan and `walk_solution`, steps equal to A2's (SC-002);
- survey S1–S3 with `walk_field` and the right total (SC-002);
- the executor's system message is base prompt + map instructions + executor instructions, and
  base prompt, tool schemas, budget and fingerprint equal A2's (SC-003);
- steps equal executor tool calls; `orchestrator_calls` equals planner + replanner calls (SC-004);
- each limit: 3 unusable plans, 3 idle subgoals, 20 turns then replanning, `{"done": true}`
  before the end (SC-005, edge cases);
- the replanner sees each finished subgoal's report and the remaining plan;
- the episode ends mid-subgoal with no further planning call.

Plus: `test_meter.py` for the new roles, `test_compare.py` for the reference, a registry/viewer
test that `plan_execute` is offered on both problems, and a report of a scripted A3 run together
with the other architectures (SC-007). The boundary test covers the new module by its glob.
