# Research: A4 Reflexion

Decisions for specs/007, each checked against the code it touches: `src/apl/dungeon/env.py`,
`frames.py`, `src/apl/survey/env.py`, `results.py`, `frames.py`, `kit.py`, `src/apl/kit.py`,
`src/apl/runner/episode.py`, `results.py`, `report.py`, `meter.py`, `registry.py`,
`src/apl/viewer/app.py`, `events.py`, `assets/index.html`.

## R1 Restart lives in the episode, not in a tool

**Decision**: each problem's `Episode` gets `restart() -> bool`, `attempt: int` (from 1) and
`max_attempts: int` (1 by default). `restart()` refuses (returns False) when the episode is over
or `attempt >= max_attempts`; otherwise it puts the world back in its start state and increments
`attempt`. Steps, invalid actions, the budget and the log are untouched; a restart costs no step.

- Dungeon: `scouts = [Scout(start, [])]`, `opened = set()`. Keys return to their rooms by
  themselves, since `keys_in_rooms` is derived from what scouts hold.
- Survey field: `scouts = [start]`, `seen = {start}`. A separate `seen_ever` keeps every cell any
  attempt saw, for the outcome's `cells_seen`.

`MAX_ATTEMPTS = 3` is a constant in each env module, next to `MAX_SCOUTS`.

**Rationale**: a restart is not an action in the world, so it is not a tool: the tool schemas and
the prompt fingerprint stay those of every other architecture (constitution I). The kit already
has one such capability, `add_scout`, which also costs no step.

**Alternatives considered**: a `restart` tool: it would change the tool descriptions for every
architecture on the problem, or for A4 only, which constitution I forbids. A new episode per
attempt with a carried-over step count: the runner, meter, viewer and results all assume one
episode object.

## R2 Only retrying architectures may restart

**Decision**: `registry.RETRYING = frozenset({"reflexion"})`. `play_episode` sets
`episode.max_attempts = MAX_ATTEMPTS` when `key.arch` is in it, else leaves it at 1. Every kit
gets `restart: Callable[[], bool]`, which calls `episode.restart()` under the kit's lock (for
other architectures it always returns False), and `max_attempts: int`, the episode's cap (1 or 3).
Both fields have defaults, so kits built elsewhere (tests) keep working.

**Rationale**: FR-003. With `max_attempts = 1` the episode code takes exactly today's paths, so
the existing architectures cannot change (SC-003).

## R3 A wrong survey total ends the attempt and restarts the field

**Decision**: in `Episode._submit`, when `max_attempts > 1`, the total is wrong and
`attempt < max_attempts`, the result is a success with data
`{"submitted": N, "correct": false, "attempts_left": k}`, the episode does not end, and the
world is restarted at once (as `restart()` does). A right total, or any total in the last allowed
attempt, ends the episode as today, with today's result `{"submitted": N}`. The log entry of the
submission belongs to the attempt that made it.

**Rationale**: FR-004, SC-004. Restarting inside the same call leaves no "attempt over" state in
which further calls would need a new error code; the next call simply plays attempt k+1. The
result tells right from wrong only, never the true total or the distance.

**Alternatives considered**: a failure result with a `wrong_total` code: it would count the
submission as an invalid action. An "attempt over" state that waits for `kit.restart()`: one more
state and an uncounted-call path, for nothing.

## R4 Logs, outcomes and frames carry the attempt

**Decision**:

- `LogEntry.attempt: int = 1`, written as `"attempt": n` only when n > 1 (as `scout` is written
  only when non-zero), so every existing log stays byte-identical.
- `Outcome.attempts: int` (the attempt the episode ended in), written only when > 1.
- Frames (`dungeon.frames.snapshot`, `survey.frames.snapshot`) get `"attempt": n` only when
  n > 1.
- `dungeon.frames.build_frames` replays restarts: before an action whose attempt is higher than
  the replay's, it calls `restart()` (with `max_attempts` set from the log). `parse_route_file`
  reads `attempt` per entry and the outcome's `attempts`; a trailing restart without a later
  action is replayed after the last action.

**Rationale**: FR-006, SC-005. The dungeon's route replay is the existing check that a saved log
rebuilds the episode; the survey field has no log replay, and its saved viewer episodes replay
from their saved events (as since specs/005).

## R5 A4's graph

**Decision**: `src/apl/arch/reflexion.py`, nodes `actor`, `act`, `reflector`, `restart`:

```text
START → actor ─(tool calls)→ act ─(more to do)→ actor
          │ (no tool call)      │ (wrong total, or MAX_STALE turns with nothing new)
          └──────→ end_attempt ←┘
end_attempt: last attempt → END; else → reflector → restart ─(refused)→ END
                                                          └─(ok)→ actor
```

- The actor's messages are A2's turn: the system message is the base prompt, A2's map
  instructions and `ACTOR_INSTRUCTIONS`; then `Attempt n of {max_attempts}.` with the notes so far (from
  attempt 2) and the start result on the attempt's first turn; then its previous reply with its
  tool results; then the map. Role `actor (attempt n)`.
- `act` applies tool calls as A2's `act` does. It counts `stale` turns: a turn whose results
  left the number of rooms (`DungeonMap.rooms`) or cells (`FieldMap.cells`) in the map unchanged.
  A wrong total is read from a submit result with `"correct": false`.
- The reflector gets the base prompt and `REFLECTOR_INSTRUCTIONS`, then the notes so far, why the
  attempt ended, the actor's last reply text and the map at the end of the attempt. Its reply text
  is the note (stripped; an empty one is not added). Role `reflector`.
- `restart`: after a wrong total the field is already restarted (R3); otherwise it calls
  `kit.restart()` and ends A4 when that is refused. Then the map is rebuilt from `kit.start` (a
  restarted world looks exactly like the start), the turn is cleared, `attempt` += 1.

Constants: `MAX_STALE = 12`. The attempt cap comes from the kit (`kit.max_attempts`, R2), since
architectures may not import the env modules; the episode enforces it either way.

**Rationale**: FR-007–FR-013. 12 stale turns allow a walk back through known rooms to a key on
L3 (at most about 8 rooms on the dev seeds) and through known cells on the field, and they are
not derived from the budget. The map is rebuilt per attempt, because the experimenter chose
"keeps only its written notes".

**Alternatives considered**: an attempt turn limit (spec FR-010 explains why not). A subgraph per
attempt: the outer loop is the point of A4 and should show in the graph.

## R6 Instruction texts

**Decision**:

`ACTOR_INSTRUCTIONS`:

> You may get up to {max_attempts} attempts. An attempt fails when you answer without a tool call, when many
> turns in a row show you nothing new, or, if the task ends with a submission, when the submitted
> answer is wrong. After a failed attempt everything is put back as it was at the start, your map
> is cleared, and you start again; the steps of every attempt count toward the one budget. Notes
> you wrote after earlier attempts are shown under "Notes from earlier attempts:".

`REFLECTOR_INSTRUCTIONS`:

> In this setup you do not call the tools yourself. An attempt has just failed. You see why it
> ended, its last reply, the map it built and the notes from earlier attempts. Write a short note
> for the next attempt, which starts again from the start with an empty map and sees only the
> notes. Answer with the note only.

**Rationale**: FR-012: they explain attempts, notes and the job, and give no advice about the
dungeon or the field. One actor text serves both problems ("if the task ends with a submission").

## R7 Results and report

**Decision**:

- `EpisodeRow.attempts: int | None` (None for non-retrying architectures, older rows and
  infrastructure errors; reports read None as 1). `completed()` takes `outcome.attempts` when the
  architecture is retrying.
- The report gains a section `## Attempts` only when some row has `attempts > 1`: per
  architecture and level, the median and the maximum attempts. Existing report text does not
  change otherwise, so the pinned dungeon report (specs/005 SC-001) stays as it is.
- `meter.LEAD_ROLES` gains `"reflector"`, so the comparison's "Calls: orch / scouts" column shows
  reflector / actor calls.
- `compare.REFERENCES["reflexion"] = "mapstate"`.

**Rationale**: FR-016, FR-017. A separate section keeps every existing table byte-identical.

## R8 Viewer

**Decision**:

- The episode gets an observer `on_restart: Callable[[], None] | None`, called after each restart
  (by `restart()` and by the wrong-total path). The viewer emits a `restart` event
  `{"attempt": n, "frame": <the start frame>}`.
- The page: on `restart`, push the frame and add a card "Attempt n starts". `render` draws the
  marker's trail and the fog from the frames of the current attempt only, and the earlier
  attempts' positions as a dashed, faded polyline (`#trail-past`). The stats panel shows
  "Attempt n / 3" for frames with an attempt.
- Saved episodes replay their saved events, so the restart events replay too.

**Rationale**: FR-018. A restart is not a step; an event of its own keeps step numbering as it is.

## R9 Constitution 2.1.0

**Decision**: amend "Experiment Setup" with one bullet, via `/speckit-constitution`, MINOR
version 2.1.0:

> - **Attempts**: an architecture registered as retrying (A4) may restart the world up to 3
>   attempts per episode. A restart puts the world back in its start state and costs no step;
>   every tool call of every attempt counts toward the one budget. On the survey field, a wrong
>   total ends such an architecture's attempt while attempts are left, with a result that says
>   only that it was wrong. Every other architecture has one attempt.

**Rationale**: FR-019. It adds a rule to a section without redefining a principle.

## R10 Tests

- Env (both problems): restart resets the world to a fresh episode's state, keeps steps; refused
  at `max_attempts`, after the end, and for `max_attempts = 1`; logs and outcomes carry attempts
  only when > 1 (SC-002, SC-003).
- Survey: wrong total with attempts left gives `correct: false`, `attempts_left`, no true total,
  restarts the field; right total and last-attempt totals end it as today (SC-004).
- Dungeon replay: an A4-like log with restarts replays through `build_frames` and
  `parse_route_file` to the same frames and end reason (SC-005).
- A4 (`tests/arch/test_reflexion.py`): give up then succeed on L1–L3 and S1–S3 with steps =
  attempt 1 + scripted A2 (SC-001); three failed attempts end it; stale turns end an attempt; a
  wrong total leads to a reflection and a fresh attempt; notes are shown; roles; prompt and budget
  equal A2's (SC-006).
- Runner, report, meter, compare, continue, dry run; viewer options, restart events, replay
  (SC-007, US2, US3).
- Pinned outputs from specs/005 still pass unchanged.
