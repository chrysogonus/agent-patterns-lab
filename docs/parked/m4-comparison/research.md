# Research: A2 Map State and the First Comparison

Decisions for M3. Each one lists the choice, why it was made, and what else was considered. M2's
decisions (specs/002-runner-react/research.md R1–R16) still hold unless one below replaces them.

## R1. A2's graph and state

**Decision**: A2 is a `StateGraph` with two keys and two nodes:

- `messages` holds **only the latest turn**: the model's last reply, then that reply's tool
  results. It has no reducer, so each write replaces it.
- `map` holds the `DungeonMap` ([data-model.md](data-model.md)).
- `agent` builds the model input from the map and `messages` (R2), calls `kit.model` with the
  tools bound, and returns `{"messages": [reply]}`.
- `act` calls `kit.tool_node(state)`, applies each tool call and its result to the map in order
  (R3), and returns `{"messages": [reply, *results], "map": map}`.
- The route is the same as A1's: after `agent`, go to `act` if the reply has `tool_calls` or
  `invalid_tool_calls`, else end. After `act`, go back to `agent`.
- It is invoked with `config={"recursion_limit": kit.recursion_limit}`, as A1 is.

**Rationale**: Without a reducer, the history never builds up in the state. FR-004 then holds
by construction rather than by trimming the history. Updating the map in the same node that runs
the tools keeps each call next to its result, so the map never sees a result without its call.

**Alternatives considered**:

- A1's `MessagesState` with the history trimmed before each model call. The history would still
  sit in the state, and the trimming is one more place to get wrong.
- A separate `update_map` node after `tools`. That adds an edge and a node for no gain.
- LangGraph's `ToolNode`. Rejected in M2 R4: it runs calls in parallel and skips step counting.

## R2. What the model sees each turn

**Decision**: Each call sends these messages, in this order:

1. `SystemMessage(kit.base_prompt + "\n\n" + MAP_INSTRUCTIONS)`.
2. On the first turn, `HumanMessage(kit.start)`, as in A1. On later turns, the previous reply
   (`AIMessage` with its tool calls) and its `ToolMessage`s.
3. `HumanMessage(rendered map)`. It comes last, so the model reads the current state just before
   it answers.

**Rationale**: This is FR-004 exactly. The model sees the result of what it just did, so it can
read an error message, and everything older reaches it only through the map. Both providers
accept a user message after tool results. OpenAI requires each `ToolMessage` to follow its
`AIMessage`, and it does. The first observation is the same message A1 gets.

**Alternatives considered**:

- The map before the previous turn. Then the newest information would sit in the middle of the
  prompt.
- No previous turn at all, only the map. The model would lose the error text of a failed call,
  and an error such as `wrong_key` is not in the map.

## R3. How the map is updated from tool results

**Decision**: `DungeonMap.apply(name, args, result)` takes one tool call (name and arguments
from the `AIMessage`) and its parsed result (the `ToolMessage` JSON, M1 format). It works only
from those values:

| Result | Map change |
| --- | --- |
| `move` with `ok`, `data` a room | Record that the current room's exit in `direction` leads to `data.label`. Record that the new room's opposite exit leads back. Then record the room (below) and make it the current room |
| `look` with `ok` | Record the room (below) |
| Record a room | Store its exits (direction → lock color or none) and items as shown now, and set the inventory from `data.inventory` |
| `take` with `ok` | Set the inventory. Remove the newly held item from the current room's items |
| `use` with `ok` (`DoorOpened`) | Clear the lock on that exit of the current room and add it to the opened doors. If the exit's destination is known, clear the opposite exit's lock there too |
| Any result with `ok: false` | No change |

The start description (`kit.start`) seeds the map as the first recorded room.

The results of the batch that ends the episode are not applied. `kit.tool_node` raises
`EpisodeEnded` as soon as a call reaches the exit or the budget, without returning the replies
of that batch. After that, no model call can happen (the meter refuses it), so nobody could ever
see that last map update. This needs no change to the kit. "After every step" in FR-001 and
SC-002 is checked for every step before the one that ends the episode, and the tests include a
batch that ends at the exit and one that ends at the budget, to show they end cleanly.

The map stores no step count and no budget. Rooms are identified by label: labels are unique
per dungeon (M1).

Failed results change nothing because the map already holds what they could reveal:

- `no_door` and `invalid_direction` concern exits that the room view already listed or left out;
- `locked` repeats a color the room view already showed.

The spec's edge case ("records nothing new except, where the error reveals it, …") therefore
amounts to no change.

**Rationale**: Every entry follows from a result A2 received. Constitution II is satisfied, and
so is the plain-code-node clause. The reverse connection comes from the base prompt's rule that
rooms are connected by doors: a door between two rooms works both ways. A2 does not peek to learn
it (US1/AC3).

**Alternatives considered**:

- Recording failed moves as "tried". With full room views, that information is redundant.
- Reading the `ToolResult` objects instead of the JSON. A2 sees the same JSON the model sees, so
  the map cannot know more than the conversation shows.

## R4. Rendering the map

**Decision**: `DungeonMap.render()` produces plain text in a fixed order: rooms in the order they
were first seen, and exits in the order north, east, south, west. Example:

```text
Your map (built from your tool results so far):
You are in: c3. Inventory: red key.
Rooms seen:
- c3 (you are here): north -> e9; east: unexplored; south: unexplored, locked (blue)
- e9: south -> c3; west: unexplored; items: green key
Doors you opened: c3 east (red).
Unexplored exits: c3 east; c3 south (locked, blue); e9 west.
```

The exit is not listed: reaching it ends the episode. The text holds only labels, directions,
colors and item names, never step counts.

**Size check (SC-003)**: an L3 dungeon has 25 rooms, and labels are short, like `c3`. All room
lines of a fully known L3 dev dungeon come to 795–807 characters (measured on the 10 seeds), so
the whole render stays under about 1,500 characters. The map is ASCII text, and every token
covers at least one character, so its character count is a guaranteed upper bound on its token
count, whatever the tokenizer. The test explores each L3 dev dungeon completely and requires the
render to be at most `num_ctx / 4` characters: 4,096 for the 16,384-token context. The real
runs confirm it: the meter records the input tokens of every A2 call in the conversation files.

**Rationale**: A deterministic order makes the render testable and keeps the prompt stable from
turn to turn, which helps a small model. The explicit "Unexplored exits" line is part of the map
named in FR-001 ("exits not yet tried"), not advice.

**Alternatives considered**: a JSON map, which costs more tokens and is harder for an 8B model to
read; an ASCII grid, which would require coordinates that the agent does not know (labels are not
coordinates).

## R5. A2's own instructions

**Decision**: `MAP_INSTRUCTIONS` only explains the map: that it is built from the agent's tool
results, that it replaces the conversation history, what "unexplored" and "locked (color)" mean,
and that the latest tool results appear just before it. It gives no strategy, such as "go to the
nearest unexplored exit" or "pick up every key".

**Rationale**: The milestone asks "does explicit memory beat history?". Strategy advice that A1
lacks would mix a prompt effect into the memory effect. Node instructions on top of the base
prompt are allowed (Constitution III). The base prompt and the tool schemas, and so the
fingerprint, stay as in M2.

**Alternatives considered**: a stronger exploration prompt, which belongs to a later architecture
or a separate prompt experiment.

## R6. Where the A2 code lives

**Decision**: two modules in `src/apl/arch/`:

- `dungeon_map.py` holds `DungeonMap`: building it from the start description, applying results,
  and rendering. It has no LangGraph imports.
- `mapstate.py` holds `play(kit)`, the graph and `MAP_INSTRUCTIONS`.

The registry gains `"mapstate": "apl.arch.mapstate"`. I (the agent) write both modules, as
the experimenter asked (spec Assumptions).

**Rationale**: plan.md has A3 and A6 build on the map, so it gets its own module. The module can
be tested without a model. Both stay inside the import boundary: `apl.arch` may import
`apl.arch`.

## R7. Testing A2 without a model

**Decision**:

- `replay_solution` in `tests/runner/scripted.py` now counts its own calls instead of counting
  `ToolMessage`s in its input. A2 does not send the history, so the old counting would replay
  step 1 forever. A1's tests are unaffected: one call still uses `per_turn` actions.
- SC-002 needs an independent check, an oracle. A test helper derives the expected map after
  each step from the layout and the M1 frames (`build_frames`):
  - the visited positions and their labels;
  - for each visited room, its doors and items as they are now, except that a door opened from
    the other side shows as still locked until a move through it makes the connection known;
  - the edges walked, in both directions;
  - the inventory.

  Tests may read the layout; architectures may not.
- The scripted routes cover a failed move, a `locked` move, a `take`, a `use`, a revisit, and
  several calls in one turn, on the `tests/dungeon/reference.py` layouts and on dev dungeons.

**Alternatives considered**: comparing the render against hand-written strings only. That covers
too few cases for "100% of steps" (SC-002). Hand-written strings stay as format checks (US1/AC3,
AC4).

## R8. Episode order in a run

**Decision**: `RunSpec.episodes()` iterates over level, seed, repeat and **then** architecture.
For the comparison that gives `react L1 1000 r1`, `mapstate L1 1000 r1`, `react L1 1000 r2`, and
so on. Before, the order was architecture first.

**Rationale**: With architecture first, an interrupted 180-episode run would hold 90 A1 episodes
and no A2 episode. Slow drift, such as a warmer GPU or a background load, would also hit one
architecture and not the other. Interleaving keeps the finished part of the run balanced and
paired. A run with one architecture plays in the same order as before.

**Alternatives considered**: a shuffled order with a fixed seed. It balances equally well but is
harder to read in the progress output.

## R9. Continuing an interrupted run

**Decision**: a new command `apl continue RUN_DIR`. It is a dry run without `--execute`
(Constitution VI). It:

1. Reads `run.json` and the rows without changing anything. A last line in `episodes.jsonl` that
   has no closing newline is a row cut off by a hard stop. It is noted, not counted, and not
   removed yet. Any other bad line exits with code 2, as `apl report` does.
2. Refuses with exit code 2 and names each difference if:
   - the current `settings.record()` differs from `run.json` in any field (including
     `prompt_fingerprint`);
   - the package versions differ;
   - the commit differs;
   - the working tree has uncommitted changes now;
   - the run was started with uncommitted changes (R10);
   - an architecture of the run is no longer registered or written.

   It also refuses, with exit code 0, a run that is already complete: nothing is played, and it
   says so.
3. Plans the episodes in run order that have no row yet, and prints how many are left with
   their upper bounds.
4. With `--execute`, and only after every check in step 2 has passed, removes the cut-off last
   line if there is one, then plays the missing episodes into the same folder through the same loop as `apl run`. Files
   of an episode that was cut off and has no row are overwritten. At the end it sets
   `completed: true` and `ended`, writes `report.md`, and prints it.

Rows of infrastructure errors count as rows, so they are not played again (FR-009: "only the
episodes that have no row yet").

**Rationale**: Every episode is written as one appended line after its files, so "has a row"
means "finished" (FR-011). Comparing the whole settings record and the code identity means a
continued run meets the same conditions as one that was never interrupted (Constitution I,
FR-010). A separate command keeps `apl run`'s required arguments as they are.

**Alternatives considered**:

- `apl run --continue RUN_DIR`. It would make `--arch`, `--level` and `--seeds` optional only
  sometimes.
- Playing infrastructure-error episodes again on continue. That would mean rewriting
  `episodes.jsonl` and having two rows for one key. R11 limits the damage instead.

## R10. Code identity

**Decision**: a run can be continued only if `code.dirty` was `false` at the start and the tree is
clean now with the same `code.commit`. The dry run of `apl run` gets a `code` line: the short
commit, followed by "uncommitted changes: this run cannot be continued" when the tree is dirty.
`results/` and `.env` are gitignored, so they do not make the tree dirty.

**Rationale**: A dirty tree cannot be compared without storing the diff. The strict rule costs
the experimenter one commit before a long run, and it makes "same code" a fact rather than a
hope (the spec's edge case).

**Alternatives considered**: storing a hash of `git diff HEAD` together with the untracked files.
It is more code, and it is still fragile because of untracked files.

## R11. Stopping when the provider is gone

**Decision**: after 3 infrastructure-error episodes in a row, the run stops. `run.json` stays
incomplete, and `apl run` and `apl continue` exit with code 4 and the message: "the provider
failed 3 episodes in a row; run stopped. Fix it, then `apl continue RUN_DIR --execute`." The 3
error rows stay.

**Rationale**: If the Ollama service stops in the middle of a night run, every remaining episode
becomes an error row within seconds (4 retries, about 7.5 s each). That would wreck SC-006 (under
5% infrastructure errors) and FR-009 would not let them be replayed. With the stop, an outage
costs at most 3 unscored episodes.

**Alternatives considered**:

- Waiting and polling until the server is back. This hides the outage and blocks the terminal.
- No guard. A single outage could then leave 100 error rows.

## R12. Comparison in the report

**Decision**: when the rows cover exactly two architectures, `report.md` gains two sections
after the existing tables. The baseline is the first architecture in the first run's
`architectures`, which is `react` for `--arch react,mapstate`.

1. **Comparison by level (FR-012)**: one row per level and metric: success rate, median
   efficiency, median tokens (input plus output per episode) and median latency. Each cell shows
   the value over all completed episodes with the min–max of the per-repeat values in
   parentheses. A difference column shows the second architecture minus the first.
2. **Per dungeon (FR-013, FR-014)**:
   - **Kept pairs**: only (level, seed, repeat) triples that both architectures completed are
     kept.
   - **Success counts**: per seed, each architecture's success rate over its kept repeats.
     Count the seeds where the second is higher, the same, or lower.
   - **Efficiency counts**: over seeds where both succeeded at least once in the kept repeats,
     compare the median efficiencies the same way.
   - **Left out**: the number of left-out triples, with the reason (one side missing, or an
     infrastructure error).
   - **Sign test**: a two-sided exact sign-test p-value on the higher/lower counts, with ties
     dropped (R13).

The section is built by `src/apl/runner/compare.py` and called from `report.render`. Its
heading repeats the dev/test notice (FR-015).

**Rationale**: Per-dungeon counts show whether a difference in averages is broad or comes from a
few dungeons (US3). Building it from pairs covers runs with different seeds or repeats
(US3/AC3) with no special cases.

**Alternatives considered**:

- Showing the comparison for any number of architectures against a baseline. This is not needed
  until M4.
- Means instead of medians. The existing report uses medians, and efficiency is skewed.

## R13. How sure the result is

**Decision**: the per-dungeon table shows the exact two-sided sign-test p-value,
`min(1, 2 · Σ_{i≤k} C(n,i) / 2^n)`, where `n` is the number of seeds that are not ties and `k` is
the smaller of the higher and lower counts. It uses `math.comb`, with no new dependency. A
footnote says that with 10 seeds the smallest possible p-value is 0.002, that it describes only
these dev seeds, and that it is not a reported result.

**Rationale**: US4 asks the conclusion to say "how sure" the numbers are. Constitution IV wants
every figure computed by code, so the conclusion quotes this value instead of guessing a
confidence. The sign test fits paired, per-dungeon outcomes and makes no assumptions about their
distribution.

**Alternatives considered**: a bootstrap confidence interval, which needs randomness and is more
code; and no measure at all, which leaves "how sure" to prose.

## R14. The written conclusion

**Decision**: `docs/findings/m3-map-state.md`, linked from the README. It contains:

- the question;
- the setup: run id, model and settings line, dev seeds, and the notice that it must not be
  reported;
- the comparison tables, copied from that run's `report.md`;
- what the numbers show per level;
- how sure they are (sign-test p-values, the number of seeds);
- the limitations (one 8B model, 10 dev seeds, A2's shorter prompts also make it faster);
- the next steps.

The agent drafts it from `report.md`, and the experimenter checks and edits it (spec
Assumptions). The check for SC-007 is to run `apl report` again on the cited run and compare the
tables (quickstart step 7).

**Rationale**: `results/` is gitignored, so the conclusion has to carry its own tables to stay
readable in the repository.

**Alternatives considered**: a conclusion inside the spec folder. Findings outlive the feature
specs and will collect across milestones.

## R15. Running the 180 episodes

**Decision**: the experimenter runs this once, on a clean committed tree, overnight:

`apl run --arch react,mapstate --level all --seeds dev --repeats 3 --execute`

It is continued with `apl continue` if it is interrupted.

Expected duration:

- A1 averaged about 190 s per episode in M2, so 90 A1 episodes take about 4.75 h.
- A2's prompts stay short (about 2,000 tokens rather than up to 16,000), so its calls are likely
  faster. A2 likely needs 3–4 h.
- The total is roughly 8–9 h.

**Rationale**: the paired, interleaved order (R8) and continuing (R9) make a single long run
practical. The run uses the M2 settings (spec Assumptions), so the A1 half can also be checked
against M2's small run.
