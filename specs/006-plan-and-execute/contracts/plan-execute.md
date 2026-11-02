# Contract: A3 `plan_execute`

Module `src/apl/arch/plan_execute.py`, written by the agent at the experimenter's request
(spec FR-011). It defines `play(kit: Kit) -> None` like every architecture and imports only
`apl.kit`, `apl.arch.*` and the problems' public tools and results (boundary test).

## Graph

Nodes `planner`, `executor`, `act`, `replanner`; transitions as in
[data-model.md](../data-model.md). Compiled once per episode and invoked with
`recursion_limit = kit.recursion_limit`.

## Prompts

Every model call starts with one system message: `kit.base_prompt`, a blank line, and the job's
instructions (research R2, R4). Nothing else is added on top of the base prompt.

| Job | System message after the base prompt | Human messages |
| --- | --- | --- |
| planner | `PLANNER_INSTRUCTIONS` | the note (if any), the start result, the map |
| replanner | `REPLANNER_INSTRUCTIONS` | the note (if any), the start result, subgoals finished with outcomes, subgoals still planned, `Steps used so far: N`, the map |
| executor | A2's map instructions for the problem, then `EXECUTOR_INSTRUCTIONS` | `Your subgoal: <text>` (+ the start result on the first executor turn), the previous reply and its tool results, the map |

The map is rendered as A2 renders it (`DungeonMap.render(False)` / `FieldMap.render()`).

## Answers

| Job | Usable answer | Effect |
| --- | --- | --- |
| planner | `{"plan": ["…", …]}`, 1–8 non-empty strings | the plan |
| replanner | `{"plan": ["…", …]}`, 1–8 non-empty strings | the subgoals still to do |
| replanner | `{"done": true}` | A3 returns; the episode ends as `stopped` |
| executor | a reply with tool calls | `act` runs them through `kit.tool_node` and updates the map |
| executor | a reply without a tool call | its text is the subgoal's report; the next subgoal starts at once, unless the report starts with `Cannot:` or no subgoal is left, which go to the replanner |

An unusable planner or replanner answer is not acted on; the next call of the same job starts
with `Your answer was not used: <reason>. Answer with one JSON object as described.`

## Limits (constants, research R5)

`MAX_SUBGOALS = 8`, `MAX_TURNS = 20`, `MAX_IDLE = 3`, `MAX_MISSES = 3` (from `apl.arch.hybrid`).

## Roles

Model calls pass `config={"metadata": {"role": ...}}`: `planner`, `replanner`,
`executor (subgoal N)` (research R7).

## Guarantees

- Only `act` calls `kit.tool_node`; planner and replanner calls cost no step.
- Nothing shown to a model comes from outside tool results and A3's own state (constitution II).
- On the same level and seed, A3's base prompt, tool schemas and budget equal A2's
  (constitution I).
- Every loop is bounded by a constant or by the step budget and token cap.
