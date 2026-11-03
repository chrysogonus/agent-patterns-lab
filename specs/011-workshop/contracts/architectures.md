# Contract: Architectures on the Workshop

Research R12. Written by the agent at the experimenter's request; reviewed by the experimenter.
Behaviour on the other problems does not change.

## Registry (`src/apl/runner/registry.py`)

`SUPPORTS` gains `workshop` for `react`, `mapstate`, `plan_execute`, `reflexion`, `supervisor`,
`hybrid`.

## WorkshopLog (`src/apl/arch/workshop_log.py`)

- `WorkshopLog.from_start(start_json)`: goal, stock and inventory from the start view.
- `apply(name, args, result)`: `look` refreshes stock and inventory; `inspect` records the recipes
  (or that the item is raw); `gather` and `craft` take the new stock and inventory from the
  result; a result with `attempts_left` changes nothing else (A4 starts a new log); failed calls
  change nothing.
- `render()`: as in data-model.md, recipes in the order they were inspected; an item with one
  recipe shows it plainly, one with two shows `recipe 1: …; recipe 2: …`. No plan, no warning.
- `known`: items inspected.
- `progress`: new inspections plus successful gathers and crafts (A4's staleness counter: a
  production phase of gathers and crafts is progress too).
- `options()`: A6's options (below).

Instructions for A2, A3, A4 and A5's helpers (`WORKSHOP_LOG_INSTRUCTIONS`), explaining the log only:

```text
You do not see the earlier conversation. Instead, every turn ends with your workshop log. It is
built from your own tool results so far: the goal, the stock, your inventory and every recipe you
have inspected. Your previous reply and its tool results come just before the log.
```

## A4

Failure reason after a stuck craft with attempts left: `stuck`; `RESTARTED` gains it. On the
workshop, as on the rune floor, `act` runs a reply's calls one at a time and stops after the first
result with `attempts_left`; the rest are dropped from the reply. The rune-only actor sentence is
joined by a workshop one: `On this workshop an attempt also fails when the goal can no longer be
made.` (`WORKSHOP_ATTEMPT`), added on the workshop only. `_size` uses `progress`.

Tests: a scripted A4 on W2 follows the greedy plan and gets stuck, then follows the reference plan:
the graph's and the episode's attempt both go from 1 to 2, one `restart` event, one reflection that
says "The attempt ended: stuck.", the steps of both attempts in one budget; a reply whose first
call leaves the goal impossible runs only that call.

## A5 on the workshop (`src/apl/arch/supervisor.py`)

The helpers become per-problem: `{"dungeon": navigator (look, move) + inventory (take, use),
"workshop": researcher (look, inspect) + crafter (gather, craft)}`, with the memory and texts of
that problem. On the workshop:

```text
SUPERVISOR (workshop): In this setup you do not call the tools yourself. You direct two helpers
who share one inventory and see the same workshop log as you. The researcher can call look and
inspect. The crafter can call gather and craft. Hand one task at a time to one helper; it reports
back when the task is done or cannot be done. Every tool call of a helper costs a step from the
budget. Answer with one JSON object and nothing else:
{"to": "researcher", "task": "<task>"}, {"to": "crafter", "task": "<task>"}, or {"done": true}
to stop.
```

The helper text is the dungeon's `_HELPER_INSTRUCTIONS` with the workshop's names and tools. A
helper's call of the other helper's tool is refused without reaching the workshop, as on the
dungeon. The dungeon's texts, helpers and tests stay as they are.

## A6 on the workshop (`src/apl/arch/hybrid.py`, a `kit.problem == "workshop"` branch)

Instructions (`WORKSHOP_HYBRID_INSTRUCTIONS`):

```text
In this setup you do not call the tools yourself. Every turn you see your workshop log and a
numbered list of actions you can take now. Code carries out the action you choose with one tool
call. Answer with the number of one option and nothing else.
```

Options, in this order: `inspect X` for each craftable named by the goal or a seen recipe and not
yet inspected (in the order first seen); `gather R (n left)` for each raw material with stock left
(stock order); `craft X with recipe k (uses a, b)` for each seen recipe whose inputs are all held
(recipe order). Answer parsing, re-asks (no step) and `MAX_MISSES` as on the dungeon.
