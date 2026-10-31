# Research: First Comparison, with Orchestrator Architectures

Decisions for `specs/004-first-comparison/spec.md`. R1–R6 cover several scouts, R7–R9 the three
orchestrators, R10–R13 the run, R14–R15 the report and the conclusion. R10–R13 come from the
parked design (`docs/parked/m4-comparison/research.md` R8–R11), adapted.

## R1. Scouts in the environment

**Decision**: `Episode` holds a list of `Scout(position, inventory)`, starting with scout 0 in the
start room. `add_scout()` appends one more in the start room and returns its number, or `None`
once there are `MAX_SCOUTS = 4`. `look`, `move`, `take`, `use` and `unknown` take a keyword
`scout: int = 0`. Doors (`opened`), the step count, the budget, the end reason and the log stay
per episode. `keys_in_rooms` leaves out keys held by any scout. `position` and `inventory` remain
as properties for scout 0, so the frames, the viewer and every caller that knows one agent keep
working.

The exit check uses the acting scout's position: the episode ends with `exit` as soon as any scout
enters the exit room, then `budget` as before.

**Rationale**: Per-scout inventories make handing a key from one region to another real work,
which is what the supervisor and blackboard patterns are meant to test (spec Assumptions). Keeping
scout 0 as "the agent" makes FR-005 (one scout behaves as before) true by construction: an episode
that never calls `add_scout` runs the same code paths on the same state.

**Alternatives considered**:

- A shared inventory. Simpler, but any scout could open any door with any key picked up anywhere,
  which removes the coordination the patterns are compared on.
- A separate multi-agent `Episode` class. It would duplicate the rules and the step accounting,
  and the two could drift apart.

## R2. Creating scouts through the kit

**Decision**: `Kit` gets `add_scout: Callable[[], Scout | None]`, where `apl.kit.Scout` is a frozen
dataclass with `number`, `tool_node` and `start` (the start room's description for that scout,
as JSON, like `kit.start`). The kit's own `tool_node` and `start` stay scout 0's. `add_scout`
costs no step and returns `None` at the limit; an architecture that gets `None` goes on with the
scouts it has (spec acceptance 1.6).

**Rationale**: Architectures may import only `apl.kit`, `apl.dungeon.tools` and
`apl.dungeon.results` (boundary test), so scouts must come through the kit. A scout's tool node has
the same shape as `kit.tool_node`, so an architecture's scout code is the same for scout 0 and the
others. The start description is what the scout would see by `look`, so nothing beyond the start
room is revealed (FR-002).

**Alternatives considered**: a `scout` argument on every tool call in the tool schemas. That would
change the base tool schemas and the prompt fingerprint for every architecture (Constitution I),
and let a model act as a scout it does not control.

## R3. Order of tool calls

**Decision**: the three orchestrators run their scouts in lockstep turns. In each turn, every
active scout's model call runs in parallel (LangGraph `Send` to one `scout` node), and then a
single `act` node applies the scouts' tool calls in scout-number order: all of scout 1's calls,
then all of scout 2's, and so on. The kit's tool node also takes a lock, so even an architecture
that calls tools from parallel branches cannot interleave two calls inside the environment.

**Revised after the first live run**: A9 (blackboard) runs one scout per turn, round robin. With
parallel turns, its four scouts saw the same board at the same moment and made the same move every
turn (a pack of four on a local qwen3.5-9b run of L1 seed 1000, out of budget at 24 steps); the
spec's "scouts take turns" asks for one at a time. A7 and A8 keep parallel turns: their scouts have
different tasks.

**Rationale**: The model calls are the slow part, so running them in parallel keeps most of the
speed. Applying the calls in a fixed order makes an episode with a scripted model play the same
way every time and makes FR-004 testable. The log records the order actually applied, so replay is
exact either way.

**Alternatives considered**:

- Each scout as a full subgraph running in its own thread. Its tool calls would interleave in
  whatever order the model answers arrive, so two runs of the same scripted episode could differ.
- Running scouts one after another, a whole task each. Deterministic, but the patterns would no
  longer differ in when scouts see each other's results.

## R4. The episode log and replay

**Decision**: `LogEntry` gets `scout: int = 0`, written to JSON only when it is not 0. `Outcome`
gets `scouts: int` (the number of scouts that made at least one tool call), written only when it is
above 1. `build_frames` takes an optional list of scout numbers parallel to the actions; a
`Frame` gets `scouts: tuple[ScoutView, ...]` with every scout's position and inventory, written as
`"scouts"` only when there is more than one. `parse_route_file` reads `scout` from outcome logs.

**Rationale**: Leaving the fields out for one scout keeps every outcome, route file and frame of the
single-agent architectures byte for byte as before (FR-005, SC-001), and older saved episodes still
parse and replay.

**Alternatives considered**: always writing `scout: 0`. Harmless, but it changes every saved file
and the tests that compare them, for no information.

## R5. Thread safety of the meter

**Decision**: the `Meter` guards its counters, the transcript and the token-cap check with a
`threading.Lock`. It also reads the role of each model call from the call's metadata
(`config={"metadata": {"role": "orchestrator"}}` or `"scout 2"`), counts orchestrator calls
separately, and records `role` in the transcript call when one is given.

**Rationale**: Parallel model calls (R3) run `on_chat_model_start` and `on_llm_end` from several
threads. Without a lock, two calls can race on the transcript's message index or the token total.
LangChain passes the invoke config's metadata to the callbacks, so the role needs no new channel.

**Alternatives considered**: one meter per scout, summed at the end. The token cap is per episode,
so it must see every call as it happens.

## R6. Roles in the viewer

**Decision**: `ViewerCallbacks` maps each model call's `run_id` to its call number and records its
role; `thinking` and `turn` events get `"role"` (or `null`). Step events get `"scout"`, and their
`call` is the latest call of that scout's role when there is one, otherwise the latest call as
before. The new-input prefix is kept per role. The page draws one marker and trail per scout in its
own color (the frame's `scouts`), labels turns "orchestrator" or "scout N", and counts every
scout's rooms as visited for "Agent's view".

**Rationale**: With parallel calls, "the latest call" no longer says which turn a step belongs to.
The role does. Single-agent architectures send no role, so their events stay as they are.

**Alternatives considered**: separate panels per scout. More layout work, and the order of turns
across scouts would be harder to follow.

## R7. One scout for all three orchestrators

**Decision**: the scout is A2's map-state agent with one extra message: its task. Each scout turn
sends the base prompt with `MAP_INSTRUCTIONS` and `SCOUT_INSTRUCTIONS`, the task, the scout's
previous reply with its tool results, and a rendered map. The pattern decides only which map: the
scout's own (fan-out), the merged map (supervisor), or the shared board with claims (blackboard).
A scout's task ends when it answers without a tool call or its step limit is used up. The shared
code is a new module `apl/arch/scouts.py`.

**Rationale**: With the same scout, a difference between the three comes from the coordination
alone (Constitution III's spirit within one comparison). A2 is then the single-agent reference for
all three (spec FR-018).

**Alternatives considered**: a ReAct scout. Its history grows per scout and would mix A1's memory
problem into the coordination question.

## R8. The merged map

**Decision**: a `SharedMap` keeps one `DungeonMap` for the rooms, plus each scout's position and
inventory. Applying scout k's call sets the map's `current` and `inventory` to scout k's, calls
`DungeonMap.apply`, and stores them back. Calls are applied in log order, so the newer
observation wins (spec edge case). `DungeonMap.render` gets an optional list of scouts to print
instead of the single "You are in" line; the blackboard adds a "Claims" line.

**Rationale**: `DungeonMap.apply` already updates rooms, doors and items from one agent's view;
switching whose view it is reuses it unchanged, so the merged map follows the same rules as A2's.

**Alternatives considered**: separate maps per scout merged room by room. That needs a time stamp
per fact to decide which observation is newer.

## R9. Orchestrator answers

**Decision**: the orchestrator answers with one JSON object, described in its instructions:

- fan-out: `{"scouts": [{"task": "...", "steps": 12}, ...]}`, at most 4 entries;
- supervisor: `{"tasks": [{"scout": 1, "task": "...", "steps": 8}, ...]}` or `{"done": true}`.

The JSON is read from the reply text (the first `{` to the last `}`). An answer that does not parse,
names an unknown scout, or asks for 0 steps is asked again with the reason, at no step cost; after
3 in a row the episode ends as stopped, as in A6. Blackboard scouts may add a line
`claim: <room> <direction>` to a reply; it is shown to the other scouts and has no other effect.

**Rationale**: The orchestrators make no tool calls, so a fixed answer format is the simplest
interface that code can check. The retry rule is A6's, so all model-driven choices fail the same way.

**Alternatives considered**: giving the orchestrator tools such as `assign(scout, task)`. They
would be node-specific tools outside the four world tools and outside the prompt fingerprint.

## R10. Episode order in a run

**Decision**: `RunSpec.episodes()` iterates level, seed, repeat, then architecture.

**Rationale**: An interrupted run then holds the same dungeons for every architecture, and slow
drift hits all of them alike. A one-architecture run plays in the same order as before.

## R11. Continuing an interrupted run

**Decision**: `apl continue RUN_DIR [--execute]`, as in the parked R9: a dry run without
`--execute`; refusals naming every difference (settings including the prompt fingerprint, package
versions, commit, a dirty tree now, a run started dirty, an architecture no longer available);
"already complete" with exit code 0; with `--execute`, a cut-off last row is removed and the missing
episodes are played into the same folder, then `completed` and `ended` are set and `report.md` is
rewritten. Infrastructure-error rows count as rows and are not replayed.

**Rationale**: "has a row" means "finished" because a row is appended after the episode's files
(FR-016). Comparing the whole record keeps a continued run under the same conditions
(Constitution I).

## R12. Code identity

**Decision**: a run can be continued only if its tree was clean at the start and is clean now at the
same commit. The dry run of `apl run` shows a `code` line with the short commit, plus "uncommitted
changes: this run cannot be continued" when the tree is dirty.

**Rationale**: as in the parked R10: a dirty tree cannot be compared without storing the diff.

## R13. Stopping when the provider fails

**Decision**: after 3 infrastructure-error episodes in a row, `apl run` and `apl continue` stop with
exit code 4, leave `run.json` incomplete, and print the `apl continue` command. After exit codes 3,
4 and 130 the command prints `continue with: uv run apl continue <RUN_DIR> --execute`.

**Rationale**: a paid run should not turn every remaining episode into an error row during an
outage, and the rows already paid for should be kept.

## R14. The comparison section of the report

**Decision**: when the completed rows cover two or more architectures, `report.md` gains a section
"Comparison" after the main table: one table per level with one row per architecture in run order,
and the columns Success, Efficiency, Steps (median), Tokens (median, input plus output),
Calls: orchestrator / scouts (median), Latency (median), Scouts (median), and the differences
"Δ success" (percentage points) and "Δ efficiency" against the architecture's reference. The
reference table is a constant in `src/apl/runner/compare.py`:

| Architecture | Reference |
| --- | --- |
| `mapstate` | `react` |
| `mapstate_routes` | `mapstate` |
| `hybrid` | `mapstate_routes` |
| `fanout`, `rounds`, `blackboard` | `mapstate` |

A cell whose reference is not in the rows shows `—`. The rows get two fields, `scouts` and
`orchestrator_calls`; older rows parse with them as `None`, shown as `—`.

**Rationale**: with one seed and one repeat per cell, a per-dungeon count or a sign test adds
nothing to this table (spec Assumptions); differences against the reference answer the questions
directly. The main table stays as in M2, so one-architecture reports do not change (FR-018).

**Alternatives considered**: the parked per-dungeon section and sign test. Kept in the parked
design for a later run with several seeds and repeats.

## R15. The written conclusion

**Decision**: `docs/findings/m4-first-comparison.md`, linked from the README. It holds the
questions, the setup (run id, model and settings line, seed 1000 of each level, the development
notice), the report's tables copied from `report.md`, what each question's rows suggest per level,
the limitation that one episode per cell cannot separate a difference from luck, the reason for 21
episodes (speed on a paid model, a first look), and next steps (more seeds and repeats on the
local model, the per-dungeon comparison). The agent drafts it, and the experimenter checks it.

**Rationale**: `results/` is gitignored, so the conclusion carries its tables (parked R14).

## R16. Expected duration and cost

**Decision**: the experimenter runs, on a clean committed tree,

`APL_MODEL=openai:gpt-6-luna uv run apl run --arch react,mapstate,mapstate_routes,hybrid,fanout,rounds,blackboard --level all --seeds dev --limit 1 --execute`

and continues it with `apl continue` if it stops.

**Rationale**: saved viewer episodes on `gpt-6-luna` averaged 46 s and 31,000 tokens. With the
orchestrators making several times as many calls, the 21 episodes should take well under two
hours. The dry run's cost is an upper bound from the token cap (21 × 2,000,000 tokens at the
higher of the two `.env` prices), far above the expected use of about 1–2 million tokens; the
experimenter can lower `APL_TOKEN_CAP` for this run if that bound is too high to accept, since the
cap is shared by all architectures (Constitution I).
