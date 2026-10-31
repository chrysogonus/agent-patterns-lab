# Contract: Orchestrator architectures A7–A9

Research R3, R7–R9. Registered names: `fanout`, `rounds`, `blackboard`. Modules:
`src/apl/arch/scouts.py` (shared), `fanout.py`, `rounds.py`, `blackboard.py`.

## The scout (shared by all three)

One scout turn is one model call with the tools bound:

```text
[system]  base prompt + "\n\n" + MAP_INSTRUCTIONS + " " + SCOUT_INSTRUCTIONS
[human]   "Your task: <task>"                       (first turn: followed by the scout's start JSON)
...       the scout's previous reply and its tool results (none on the first turn)
[human]   <the map for this pattern, rendered>
```

- `SCOUT_INSTRUCTIONS` explains the task line and that other scouts exist; it gives no strategy.
- The call carries `config={"metadata": {"role": "scout N"}}`.
- The turn's tool calls are applied by the `act` node (below), not inside the scout node.
- A scout's task ends when it answers without a tool call, or when its step limit is used up.
  Steps of a task count only the calls actually applied for that scout.

## The lockstep turn (shared)

```text
dispatch ──Send(scout n) for every active scout──→ scout (parallel model calls)
                                                       │ replies: [(n, AIMessage)]
                                                       ▼
                                                     act: for n in sorted order:
                                                            run n's calls through its tool node,
                                                            update the maps, its steps_left, done
```

- `act` applies calls in scout-number order, all of one scout's calls before the next scout's.
- `EpisodeEnded` from any tool node ends the graph, as for every architecture.

## A7 fan-out once (`fanout`)

```text
START → orchestrate (1 model call, role "orchestrator") → lockstep turns until every scout is done → END
```

- Orchestrator input: base prompt + `FANOUT_INSTRUCTIONS`, the start room JSON, and the answer
  format. Like every architecture, it is not told the budget.
- Answer: `{"scouts": [{"task": "<text>", "steps": <int ≥ 1>}, ...]}` with 1–4 entries. Scout 0 is
  the first entry; the others are created with `kit.add_scout()`.
- Each scout sees **its own map only**, built from its own tool results. It never sees another
  scout's results.
- When every scout is done and no one reached the exit, the graph ends (scored as stopped).

## A8 supervisor in rounds (`rounds`)

```text
START → plan (role "orchestrator") → lockstep turns until every tasked scout is done → plan → ... → END
```

- Orchestrator input each round: base prompt + `ROUNDS_INSTRUCTIONS`, the merged map with every
  scout's room and inventory, the steps used so far, the result of the last round (which scouts
  finished, which stopped at their limit, which call failed), and the answer format.
- Answer: `{"tasks": [{"scout": <0–3>, "task": "<text>", "steps": <int ≥ 1>}, ...]}` or
  `{"done": true}`. A scout number not yet in use is created with `kit.add_scout()`; if that
  returns `None`, the task is dropped and the next round's input says so.
- Each scout sees the merged map **as it was at the start of the round**, plus its own results of
  this round applied on top.
- `{"done": true}` ends the graph.

## A9 shared blackboard (`blackboard`)

```text
START → create 4 scouts → one scout's turn (round robin) → act → next scout ... until every scout is done → END
```

- There is no orchestrator call. Every scout gets the same task: "Find the exit. Other scouts
  explore the same dungeon; the board shows what all of you have seen and which exit each of you
  has claimed."
- Unlike A7 and A8, **one scout acts at a time**: the active scout with the fewest turns, lowest
  number first. In the first live run with parallel turns, all four scouts saw the same board at
  the same moment and moved as one pack; taking turns lets each see the previous scout's move and
  claim.
- Each scout sees the **live board**: the merged map after every applied call, every scout's room
  and inventory, and a line `Claims: scout 1 → k7 north; ...`.
- A reply may contain a line `claim: <room> <direction>`; it replaces that scout's claim. Claims have
  no other effect.

## Answers the orchestrator gets wrong

Shared by A7 and A8 (research R9):

- The JSON is read from the reply text, from the first `{` to the last `}`.
- An answer is invalid if it does not parse, has the wrong shape, names a scout outside 0–3, or asks
  for fewer than 1 step. It is asked again with one line naming the problem, at no step cost.
- After 3 invalid answers in a row, the graph ends (scored as stopped).

## What the tests check

- With scripted answers, each architecture succeeds on a dev dungeon of each level.
- The merged map equals what all scouts' tool results revealed, after every applied call.
- A7: exactly one orchestrator call; no scout input contains another scout's results.
- A8: each orchestrator input contains the merged map and the steps used.
- A9: each scout input contains every scout's room and every claim; scouts act one at a time in
  turn.
- Two plays of the same scripted episode give identical logs.
