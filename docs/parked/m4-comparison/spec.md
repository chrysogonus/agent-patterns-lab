# Feature Specification: A2 Map State and the First Comparison

**Feature Branch**: `003-map-state-comparison` (spec directory; no git branch is created)

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "M3 A2 map state and the first comparison"

## User Scenarios & Testing *(mandatory)*

The users of this feature are the experimenter, who runs the comparison and writes up what it
shows, and the two architectures being compared. A1 ReAct exists from M2: its only memory is the
message history. A2 keeps an explicit map of what it has explored in its graph state and shows
it to the model every turn. M3 answers plan.md's first question, "does explicit memory beat
history?", with 2 architectures × 3 levels × 10 seeds × 3 repeats = 180 episodes and a written
conclusion.

### User Story 1 - Play A2 with an explicit map (Priority: P1)

A2 explores the dungeon like A1, but after every tool result it updates a map in its state. The
map covers the rooms seen, the exits of each room with their lock colors, which exit leads to
which room, the items seen and where, the current room, the inventory, and which exits have not
been tried yet. Every turn the model sees this map, rendered as text, in place of the message
history: besides the map it sees only its previous reply and that reply's tool results (FR-004).
The map is built only from tool results, never from the environment.

**Why this priority**: Without A2 there is nothing to compare. Its map is also the first piece of
explicit state in the lab, which later architectures (A3, A6) build on.

**Independent Test**: Play A2 with a scripted model on hand-built dungeons. After every step,
compare A2's map with what the tool results so far reveal, and check what the model was shown.

**Acceptance Scenarios**:

1. **Given** A2 and a scripted model that replays the shortest solution, **When** it plays a dev
   dungeon of each level, **Then** every episode succeeds in the optimal number of steps.
2. **Given** a scripted sequence of moves, including a failed one, **When** A2 plays it, **Then**
   after each step the map contains exactly the rooms, exits, connections, locks and items the
   tool results have revealed so far, and nothing else.
3. **Given** A2 has moved east from room X to room Y, **When** the map is rendered, **Then** it
   shows that X's east exit leads to Y, and that Y's west exit leads back to X.
4. **Given** a locked door that A2 later opened, **When** the map is rendered, **Then** the door
   is shown as opened, and the key shows as being in the inventory.
5. **Given** any turn after the first, **When** the model is called, **Then** its input contains
   the shared base prompt, A2's own instructions, the current rendered map, and the model's
   previous reply with its tool results, and no earlier messages.
6. **Given** a long episode, **When** the model is called for step 30, **Then** none of the model
   replies or tool results from steps 1–28 is in its input.
7. **Given** the architecture source files, **When** the boundary checks run, **Then** A2 uses
   only the four tools, the agent-facing results and the shared setup.

---

### User Story 2 - Run the comparison as one fair run (Priority: P2)

The experimenter runs A1 and A2 on the same levels, seeds and repeats, with the same model and
settings, in one run. The run takes hours on the local model, so it must survive interruptions:
an interrupted run can be continued, playing only the episodes that are missing.

**Why this priority**: The comparison is the point of the milestone. A 180-episode local run
takes many hours, and starting over after a crash or a reboot would make it impractical.

**Independent Test**: Start a scripted 2-architecture run, interrupt it partway, continue it, and
check that the finished run has every episode exactly once with the same settings record.

**Acceptance Scenarios**:

1. **Given** the run "A1 and A2 on L1–L3, the comparison seeds, 3 repeats", **When** it is
   planned, **Then** the dry run shows 180 episodes, an upper bound on model calls and tokens,
   and both architectures under one set of settings.
2. **Given** an interrupted run with some episodes finished, **When** the experimenter continues
   it, **Then** only the missing episodes are played, the finished ones are kept unchanged, and
   the run is marked complete at the end.
3. **Given** an interrupted run, **When** the experimenter tries to continue it with different
   settings or a different code version, **Then** continuing is refused with a message naming
   what differs.
4. **Given** a finished run, **When** the report is built, **Then** A1 and A2 appear side by side
   for each level.

---

### User Story 3 - Compare the two architectures fairly (Priority: P3)

The report shows, for each level, how A1 and A2 differ: success rate, median efficiency, tokens
and latency, each with its spread across repeats. Because both played exactly the same dungeons,
it also compares them dungeon by dungeon: on how many seeds A2 did better, the same, or worse
than A1.

**Why this priority**: Averages alone can hide that one architecture wins on a few dungeons and
loses on many. The per-dungeon view is what makes the comparison trustworthy.

**Independent Test**: Build the comparison from hand-written runs with known outcomes and check
every figure by hand.

**Acceptance Scenarios**:

1. **Given** two architectures on the same seeds and repeats, **When** the comparison is built,
   **Then** for each level it shows each architecture's success rate and median efficiency with
   their spread, and the difference between them.
2. **Given** the same, **When** the per-dungeon comparison is built, **Then** for each level it
   counts the seeds where A2's success rate over the repeats is higher, equal or lower than A1's,
   and does the same for median efficiency over seeds both solved.
3. **Given** runs that did not use the same seeds and repeats for both architectures, **When** a
   per-dungeon comparison is requested, **Then** it covers only the seeds both played and says so.

---

### User Story 4 - Write down what the comparison shows (Priority: P4)

The experimenter records the result in a written conclusion kept in the repository: the question,
the setup, the report's tables, what the numbers show, how sure they are, and what to try next.

**Why this priority**: The milestone is done when the conclusion exists (plan.md M3). It depends
on Stories 1–3.

**Independent Test**: Check the conclusion against the run it cites: every number in it appears
in that run's report.

**Acceptance Scenarios**:

1. **Given** a finished comparison run, **When** the conclusion is written, **Then** it names the
   run, the model and settings, the seed set and whether the result may be reported, and every
   number it quotes matches the report.
2. **Given** the conclusion, **When** it is read, **Then** it states at least one limitation (for
   example the number of seeds or the model) and at least one next step.

---

### Edge Cases

- A tool result fails (for example a move into a wall): the map records nothing new except, where
  the error reveals it, that the direction has no door or is locked.
- A2 moves through a door it has not seen from the other side: the connection is recorded in both
  directions.
- Room labels are opaque, so two different rooms never share a label; A2 relies on labels to know
  it has returned to a room.
- The rendered map grows with the dungeon: on the largest level it must still fit well inside the
  model's context together with the base prompt.
- A run is continued after the code changed (uncommitted edits or a new commit): continuing is
  refused, because the two halves would not have identical conditions.
- A run is continued when it is already complete: nothing is played and the run says so.
- An episode was cut off mid-way by the interruption: it is played again from the start, never
  half-kept.
- One architecture has infrastructure-error episodes that the other has not: the per-dungeon
  comparison leaves out that seed and repeat for both, and says how many were left out.

## Requirements *(mandatory)*

### Functional Requirements

**A2 map state**

- **FR-001**: A2 MUST keep a map of the dungeon in its graph state, updated after every tool
  result, holding: the rooms seen (by label), each room's exits with their lock colors as last
  seen, which exit leads to which room once it has been used, the items seen and in which room,
  the current room, the inventory, the doors it has opened, and the exits not yet tried.
- **FR-002**: The map MUST be built only from the tool results A2 has received (Constitution II).
  A2 MUST NOT read the layout, the solver or any other environment internal.
- **FR-003**: A2 MUST render the map as text and give it to the model on every turn, together
  with the shared base prompt and A2's own instructions on top of it (Constitution III).
- **FR-004**: The map MUST replace the message history. Besides the base prompt, A2's instructions
  and the rendered map, the model MUST see only its previous reply and the tool results of that
  reply (on the first turn: the shared starting message). Earlier messages MUST NOT be sent.
- **FR-005**: A2 MUST use the shared model, tools and tool node, and finish when the model answers
  without a tool call or the episode ends, as A1 does.
- **FR-006**: A2 MUST be selectable by name (`mapstate`) and pass the same boundary checks as A1.

**Comparison run**

- **FR-007**: The comparison MUST be one run with both architectures, so that both share the same
  settings record, prompt fingerprint and code version.
- **FR-008**: The comparison MUST use 3 levels × 10 seeds × 3 repeats per architecture from the
  dev seeds, as plan.md M3 says. Its report and the conclusion MUST be headed as a development
  result that must not be reported as final (Constitution V); the test seeds stay unused.
- **FR-009**: An interrupted run MUST be continuable: continuing plays only the episodes that have
  no row yet, keeps the finished rows and files unchanged, and marks the run complete when the
  last episode is done.
- **FR-010**: Continuing MUST be refused if the settings, the prompt fingerprint, the code version
  or the uncommitted-changes state differ from the run's settings record, naming what differs.
- **FR-011**: An episode interrupted mid-way MUST leave no row and no partial files that count as
  finished; it is played again when the run is continued.

**Comparison report**

- **FR-012**: For each level, the report MUST show each architecture's success rate, median
  efficiency, median tokens and median latency with the spread across repeats, and the difference
  between the architectures (A2 minus A1).
- **FR-013**: For each level, the report MUST compare the architectures per dungeon: the number of
  seeds where A2's success rate over the repeats is higher, equal and lower than A1's, and, over
  seeds both solved at least once, the number where A2's median efficiency is higher, equal and
  lower.
- **FR-014**: The per-dungeon comparison MUST use only seed and repeat pairs that both
  architectures completed, and MUST state how many were left out.
- **FR-015**: The comparison MUST be computed by code from the rows (Constitution IV) and MUST
  carry the same dev-or-test heading as every report (Constitution V).

**Written conclusion**

- **FR-016**: The conclusion MUST be a document in the repository that names the run id, the model
  and settings, the seed set and whether the result may be reported, and includes the report's
  tables.
- **FR-017**: The conclusion MUST state the answer to "does explicit memory beat history?" for
  each level as the numbers show it, at least one limitation, and at least one next step. Every
  number it quotes MUST match the report.

### Key Entities

- **Map (A2 state)**: Rooms by label with their exits, lock colors, known connections and items;
  the current room, inventory, opened doors and untried exits. Built only from tool results.
- **Rendered map**: The text form of the map shown to the model each turn.
- **Comparison run**: One run with both architectures, all levels, the comparison seeds and
  3 repeats; continuable after an interruption.
- **Per-dungeon comparison**: For each level and seed, which architecture did better on success
  rate and on efficiency.
- **Conclusion**: The written result of the milestone, tied to one run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the scripted model replaying the shortest solution, A2 succeeds with efficiency
  1.0 on 100% of the dev dungeons of all three levels.
- **SC-002**: For scripted episodes on at least 5 hand-built or generated dungeons, A2's map after
  every step matches exactly what the tool results have revealed, in 100% of steps.
- **SC-003**: On the largest dev dungeon, fully explored, the rendered map takes less than a
  quarter of the model's context window.
- **SC-004**: A scripted run interrupted at least twice and continued each time ends with every
  planned episode exactly once, and its rows equal those of an uninterrupted run of the same
  scripted episodes.
- **SC-005**: Every figure in the comparison built from hand-written runs matches a hand
  calculation, including the per-dungeon counts and the left-out pairs.
- **SC-006**: The comparison run completes all 180 episodes, with infrastructure errors (if any)
  listed separately and making up less than 5% of episodes.
- **SC-007**: The written conclusion exists, cites the run, and 100% of the numbers it quotes match
  that run's report.

## Assumptions

- The model is the local `ollama:qwen3:8b` with the M2 settings (16,384-token context, 4,096
  output tokens per call), unless the experimenter changes it before the run. The comparison is
  only valid between architectures in the same run.
- The experimenter has asked the agent to write A2's graph (`src/apl/arch/mapstate.py`),
  including the map update and its rendering, as with A1.
- A2's map rendering and its node instructions are part of A2 (graph logic), not shared setup.
  The base prompt and tool descriptions stay exactly as in M2, so the prompt fingerprint is the
  same for both architectures.
- The M2 small run took about 190 seconds per episode on average on the local model, so 180
  episodes take roughly 8–10 hours, which is why continuing an interrupted run (FR-009) is in
  scope. Running episodes in parallel is not.
- A1 is not changed in M3, so its results stay comparable with M2's runs of the same settings.
- The conclusion is written by the experimenter. An agent may draft it from the report, and the
  experimenter checks and edits it.
- No LLM judges anything: the conclusion interprets numbers the code computed.
