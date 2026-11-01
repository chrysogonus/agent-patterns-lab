# Contract: A5 `supervisor`

Module `src/apl/arch/supervisor.py`, written by the agent at the experimenter's request (spec
FR-010). `play(kit: Kit) -> None`; imports only `apl.kit`, `apl.arch.*` and the dungeon's public
tools and results. Registered for the dungeon only.

## Graph

Parent nodes `supervisor`, `navigator`, `inventory`; each helper is a compiled subgraph with nodes
`helper` and `act` over the same state. Transitions in [data-model.md](../data-model.md). Invoked
with `recursion_limit = kit.recursion_limit`.

## Prompts

| Job | System message | Human messages | Tools | Role |
| --- | --- | --- | --- | --- |
| supervisor | base prompt, `SUPERVISOR_INSTRUCTIONS` | note (if any); start result; `Handoffs so far:` …; `Steps used so far: N`; the map | none | `supervisor` |
| navigator | base prompt, A2's `MAP_INSTRUCTIONS`, `NAVIGATOR_INSTRUCTIONS` | `Your task: <task>` (+ start result on the first helper turn of the episode); previous reply and its results; the map | `look`, `move` | `navigator (task n)` |
| inventory | base prompt, A2's `MAP_INSTRUCTIONS`, `INVENTORY_INSTRUCTIONS` | as the navigator | `take`, `use` | `inventory (task n)` |

Texts per research R6. Supervisor answers per R4.

## Constants

`MAX_TURNS = 20` and `MAX_IDLE = 3` from `apl.arch.plan_execute`; `MAX_MISSES = 3` from
`apl.arch.hybrid`.

## Guarantees

- Only a helper's `act` calls `kit.tool_node`; supervisor calls cost no step.
- A helper's call to the other helper's tool never reaches the dungeon: it is answered with
  `Not made: <tool> is the navigator's tool. It cost no step.` (or `the inventory helper's`;
  status `error`) and is not applied to the map. All other calls go to the dungeon in the reply's order.
- One map for all jobs, built only from dungeon tool results.
- Nothing shown to a model comes from outside tool results, the reports and A5's own counters.
- On the same level and seed, A5's base prompt, tool schemas and budget equal A2's.
