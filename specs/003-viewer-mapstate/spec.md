# Feature Specification: Browser Viewer and A2 Map State

**Feature Branch**: `003-viewer-mapstate` (spec directory; no git branch is created)

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "M3 browser viewer and A2 map state: a local web page where I pick a
level and seed (regenerate the same dungeon any time), pick an agent architecture (A1 ReAct, A2
map state; later ones appear automatically) and watch it play live, with the model's messages,
stats, the agent's knowledge (fog of war, A2's map text) and a shortest-solution toggle; finished
episodes saved and replayable. A2 keeps an explicit map in graph state that replaces the message
history (design carried over from docs/parked/m4-comparison). The 180-episode comparison is
parked for M4."

## User Scenarios & Testing *(mandatory)*

The user of this feature is the experimenter, who wants to understand how the agent
architectures behave by watching them, before measuring them at scale. The current M2 output only
helps afterwards: a report and per-episode files, plus an animation that has to be built by hand.
M3 gives the experimenter one page in the browser. There they pick a dungeon, pick an
architecture and watch it think and move.

M3 also adds the second architecture, A2. A2 keeps an explicit map of what it has explored and
shows it to the model every turn, in place of the conversation history. With two architectures
side by side, watching them becomes interesting.

The full A1 vs A2 comparison (180 episodes, continuable runs, comparison report, written
conclusion) is out of scope. It is parked for M4, and its worked-out design is in
`docs/parked/m4-comparison/`.

### User Story 1 - Browse dungeons by level and seed (Priority: P1)

The experimenter opens the viewer, picks a level (L1, L2, L3) and a seed, and sees the dungeon
drawn:

- the rooms with their labels, the doors, and the locked doors in their colors;
- the keys, the start and the exit;
- the step budget and the length of the shortest solution.

Choosing the same level and seed again always shows the identical dungeon. A toggle draws the
shortest solution on top.

**Why this priority**: The dungeon is what every agent is measured on. Being able to look at any
dungeon quickly is the basis for watching agents, and it is useful on its own.

**Independent Test**: Open the viewer, show L3 seed 1000, then seed 4242, then seed 1000 again.
The first and third pictures are identical and the second differs. The shortest-solution toggle
draws a route from the start to the exit that is as long as the stated optimum.

**Acceptance Scenarios**:

1. **Given** the viewer is open, **When** the experimenter picks a level and a dev seed, **Then**
   the dungeon is drawn with every room, door, lock, key, the start and the exit, and the page
   states its budget and optimal step count.
2. **Given** a dungeon is shown, **When** the same level and seed are chosen again, even after
   restarting the viewer, **Then** the drawing is identical.
3. **Given** a dungeon is shown, **When** the shortest-solution toggle is turned on, **Then** the
   route of the shortest solution is drawn from the start to the exit, including the detours for
   keys. Turned off, it disappears.
4. **Given** the seed field, **When** the experimenter asks for a random seed, **Then** a new seed
   is chosen that is not one of the test seeds, and its dungeon is shown.
5. **Given** the seed field, **When** the experimenter enters one of the test seeds, **Then** the
   dungeon is not shown, and a message explains that test seeds are reserved for reported
   results.
6. **Given** the seed field, **When** the experimenter enters something that is not a whole
   number ≥ 0, **Then** a clear message is shown and the previous dungeon stays.

---

### User Story 2 - Watch an agent play live (Priority: P2)

With a dungeon shown, the experimenter picks an architecture from a list of every architecture
that exists and starts it. While it plays, the page shows:

- **On the map:** each move as it happens, with the agent's position, its trail, failed actions,
  keys picked up and doors opened.
- **In a side panel:** what the model does each turn: its text and reasoning, the tool calls it
  made, and the results it got back.
- **Running statistics:** steps used out of the budget, model calls, tokens and elapsed time.

The experimenter can stop the agent, scrub back to any earlier step, and switch on an "agent's
view" that dims the rooms the agent has not been in yet.

**Why this priority**: Watching an agent work is the point of this milestone. It shows where an
architecture goes wrong (circling, giving up, ignoring a key) in a way that summary numbers
cannot.

**Independent Test**: With a scripted stand-in for the model, start an episode on a known dungeon
and check that each step, each model turn and the final statistics appear in the page in the
right order, and that stopping works.

**Acceptance Scenarios**:

1. **Given** a dungeon is shown, **When** the experimenter opens the architecture list, **Then**
   it shows every architecture that exists (A1 ReAct and A2 map state in this milestone). An
   architecture added later appears without changes to the page.
2. **Given** an architecture is chosen, **When** the experimenter starts it, **Then** the episode
   runs on exactly the dungeon shown, with the same model and settings as the command-line runner
   would use. The page names the model.
3. **Given** a running episode, **When** the agent makes a tool call, **Then** the map and the
   statistics show it within one second: the new position or the failure, a key taken, a door
   opened.
4. **Given** a running episode, **When** a model turn finishes, **Then** the side panel adds the
   turn:
   - its text and reasoning, with long parts collapsed;
   - each tool call with its result;
   - any new input the model received that turn, such as A2's map.
5. **Given** a running episode, **When** the model is still working on a turn, **Then** the page
   shows that it is waiting for the model and for how long.
6. **Given** a running episode, **When** the experimenter presses Stop, **Then** the episode
   ends as stopped once the current model turn is over, and the result is shown.
7. **Given** an episode, live or finished, **When** the experimenter moves the step control back,
   **Then** the map shows the state at that step. Moving forward again, or to "live", follows the
   episode once more.
8. **Given** the agent's view is on, **When** the map is drawn, **Then** rooms the agent has not
   been in yet are dimmed, and the rooms it has been in are drawn normally.
9. **Given** an episode has ended, **When** the result is shown, **Then** it states how it ended
   (exit, budget, stopped, or an error), the steps against the optimum, the efficiency on
   success, the model calls, the tokens and the time.
10. **Given** an episode is running, **When** the experimenter tries to start another one,
    **Then** it is refused with a message, because only one episode runs at a time.

---

### User Story 3 - A2: an agent with an explicit map (Priority: P3)

A2 explores like A1, but after every tool result it updates a map that it keeps itself. The map
holds:

- the rooms seen, with their exits and lock colors;
- which exit leads to which room;
- the items seen and where they are;
- the current room and the inventory;
- the doors opened, and the exits not yet tried.

Every turn the model sees this map as text, **in place of** the conversation history. Besides the
map it sees only its previous reply and that reply's tool results. The map is built only from tool
results, never from the environment.

**Why this priority**: A second architecture makes watching worthwhile, and A2 tests plan.md's
first question: does explicit memory beat history? It is also the first piece of explicit state
in the lab, which later architectures (A3, A6) build on.

**Independent Test**: Play A2 with a scripted model on hand-built and generated dungeons. After
every step, compare A2's map with what the tool results so far reveal, and check what the model
was shown.

**Acceptance Scenarios**:

1. **Given** A2 and a scripted model that replays the shortest solution, **When** it plays a dev
   dungeon of each level, **Then** every episode succeeds in the optimal number of steps.
2. **Given** a scripted sequence of moves, including a failed one, **When** A2 plays it, **Then**
   after each step, up to the one that ends the episode, the map contains exactly the rooms,
   exits, connections, locks and items the tool results have revealed so far, and nothing else.
3. **Given** A2 has moved east from room X to room Y, **When** the map is rendered, **Then** it
   shows that X's east exit leads to Y, and that Y's west exit leads back to X.
4. **Given** a locked door that A2 later opened, **When** the map is rendered, even several turns
   later, **Then** the door is shown as opened with its color, and the key shows as being in the
   inventory.
5. **Given** any turn after the first, **When** the model is called, **Then** its input contains
   the shared base prompt, A2's own instructions, the model's previous reply with its tool results,
   and the current rendered map, and no earlier messages.
6. **Given** a long episode, **When** the model is called for step 30, **Then** none of the model
   replies or tool results from steps 1–28 is in its input.
7. **Given** the architecture source files, **When** the boundary checks run, **Then** A2 uses
   only the four tools, the agent-facing results and the shared setup.
8. **Given** A2 running in the viewer, **When** a model turn is shown, **Then** the side panel
   shows the map text A2 gave the model that turn.

---

### User Story 4 - Replay saved episodes (Priority: P4)

Every episode played in the viewer is saved. The experimenter can pick a saved episode from a list
and watch it again with the same map, side panel and statistics as live, at any speed and step by
step.

**Why this priority**: An episode takes minutes on the local model. Being able to look at it again
later, or to show it to someone, avoids playing it again.

**Independent Test**: Play a scripted episode in the viewer, then open it from the saved list. Its
steps, model turns and statistics are identical to what was shown live.

**Acceptance Scenarios**:

1. **Given** an episode ended in any way (exit, budget, stopped, error), **When** the experimenter
   opens the saved list, **Then** it is listed with its architecture, level, seed, how it ended,
   and when it was played.
2. **Given** a saved episode, **When** it is opened, **Then** the dungeon, every step, every model
   turn and the final statistics are shown as they were live, and it can be played, paused and
   scrubbed.
3. **Given** a saved episode, **When** its files are used with the existing command-line tools,
   **Then** they work there too: the route animation and the step table.

---

### Edge Cases

- **The viewer is closed or reloaded during a run.** The episode keeps running and is saved. On
  reopening, the page catches up to everything that happened so far and follows it live.
- **The model service is not running or fails mid-episode.** The page shows the error. The
  episode is saved as an error, and the viewer stays usable.
- **The configured model is a paid provider.** Starting an agent is refused unless the viewer was
  started with the explicit permission to make paid calls (Constitution VI). Browsing dungeons and
  replaying saved episodes always work.
- **The model makes several tool calls in one turn.** Each appears as its own step, in order,
  under that turn.
- **The model produces very long reasoning.** It is collapsed in the panel and can be expanded.
- **Stop is pressed while a model turn is in progress.** The turn finishes (it cannot be cut
  off), then the episode ends as stopped. The page says it is stopping.
- **A seed outside both seed sets, for example 4242.** It is allowed and counts as development
  use, like the dev seeds.
- **A saved episode's architecture was later removed or renamed.** The episode still replays,
  because replay needs no architecture.
- **A2 reaches the exit with several calls in its last turn.** The episode ends at the exit. The
  map's last update is never shown to the model, because no model call follows.
- **Two browser tabs are open.** Both show the same running episode. Neither can start a second
  one.

## Requirements *(mandatory)*

### Functional Requirements

**Viewer: dungeons**

- **FR-001**: The viewer MUST be a page in the experimenter's browser, served by the lab itself.
  It MUST be reachable only from the same machine.
- **FR-002**: The viewer MUST accept the levels L1–L3 and any whole-number seed ≥ 0. The same
  level and seed MUST always show the identical dungeon.
- **FR-003**: The dungeon drawing MUST show every room with its label, every door, every lock in
  its color, every key, the start and the exit. The page MUST state the step budget and the
  optimal step count.
- **FR-004**: A toggle MUST draw and remove the shortest solution on the map.
- **FR-005**: The viewer MUST refuse the test seeds with an explanation (Constitution V). It MUST
  offer the dev seeds as quick choices, and a random seed that is never a test seed.

**Viewer: watching an agent**

- **FR-006**: The architecture list MUST contain every architecture that is registered and
  written, without page changes when one is added.
- **FR-007**: An episode started in the viewer MUST play the shown dungeon with the shared model
  and settings, exactly as the command-line runner plays an episode (Constitution I). The viewer
  only observes: it MUST NOT give the agent anything beyond the four tools.
- **FR-008**: Every tool call MUST appear in the page within one second: the position, the trail,
  failed actions, keys taken and doors opened.
- **FR-009**: Every model turn MUST appear in the side panel with:
  - its text and any reasoning the model provides;
  - its tool calls, each with its result;
  - any input to the model that the page has not shown yet, such as A2's map.

  The page MUST show while a model turn is in progress, and for how long.
- **FR-010**: The page MUST show running statistics: steps used and budget, optimal steps, model
  calls, tokens and elapsed time. At the end it MUST also show the end reason and, on success, the
  efficiency.
- **FR-011**: An "agent's view" toggle MUST dim the rooms the agent has not been in yet.
- **FR-012**: A Stop control MUST end the episode as stopped after the current model turn.
- **FR-013**: Only one episode MUST run at a time. Starting another MUST be refused with a
  message.
- **FR-014**: A page opened or reloaded during an episode MUST catch up to every step and turn
  so far, then follow live.
- **FR-015**: The experimenter MUST be able to move to any step of the episode, live or finished,
  and back to live.
- **FR-016**: Starting an agent MUST be refused for a paid provider unless the viewer was started
  with explicit permission for paid calls (Constitution VI). Without it, browsing and replay MUST
  still work.
- **FR-017**: A provider failure MUST be shown in the page. The episode MUST be saved as an error,
  and the viewer MUST stay usable.

**Viewer: saved episodes**

- **FR-018**: Every episode started in the viewer MUST be saved when it ends, whatever the way it
  ends. The saved files MUST hold its steps, its model conversation and its statistics, in the
  formats the command-line tools already read.
- **FR-019**: The viewer MUST list saved episodes, newest first, with architecture, level, seed,
  end reason and time. A saved episode MUST replay with the same map, panel and statistics as
  live.

**A2 map state**

- **FR-020**: A2 MUST keep a map of the dungeon in its graph state, updated after every tool
  result, holding:
  - the rooms seen (by label);
  - each room's exits with their lock colors as last seen;
  - which exit leads to which room once it has been used;
  - the items seen and in which room;
  - the current room and the inventory;
  - the doors it has opened, with their colors;
  - the exits not yet tried.

  The results of the batch that ends the episode need not be applied, because no model call
  follows them.
- **FR-021**: The map MUST be built only from the tool results A2 has received (Constitution II).
  A2 MUST NOT read the layout, the solver or any other environment internal.
- **FR-022**: A2 MUST render the map as text and give it to the model on every turn, together with
  the shared base prompt and A2's own instructions on top of it (Constitution III). The
  instructions MUST explain the map and MUST NOT add strategy advice.
- **FR-023**: The map MUST replace the message history. Besides the base prompt, A2's instructions
  and the rendered map, the model MUST see only its previous reply and the tool results of that
  reply (on the first turn: the shared starting message). Earlier messages MUST NOT be sent.
- **FR-024**: A2 MUST use the shared model, tools and tool node, and finish when the model answers
  without a tool call or the episode ends, as A1 does.
- **FR-025**: A2 MUST be selectable by name (`mapstate`) in the viewer and on the command line,
  and pass the same boundary checks as A1.

### Key Entities

- **Dungeon view**: The drawing of one dungeon (level and seed), with its budget, its optimum and
  its shortest solution.
- **Live episode**: One architecture playing one dungeon, observed as a stream of steps and model
  turns, ending with statistics.
- **Step**: One tool call: the action, its result, and the agent's position, inventory and opened
  doors after it.
- **Model turn**: One model call: its new input, its text, its reasoning, its tool calls and its
  token usage.
- **Saved episode**: A finished live episode on disk: steps, conversation, statistics and the
  settings it ran with.
- **Map (A2 state)**: Rooms by label with their exits, lock colors, known connections and items;
  the current room, inventory, opened doors and untried exits. Built only from tool results.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Showing a dungeon of any level after choosing level and seed takes under 2 seconds.
  The same level and seed give an identical drawing in 100% of tries, including across restarts.
- **SC-002**: During a live episode, each step appears in the page within 1 second of the tool
  call, in 100% of steps.
- **SC-003**: Reopening the page during an episode shows every step and model turn so far within
  2 seconds, and then follows live.
- **SC-004**: A saved episode replays with exactly the steps, model turns and statistics shown
  live, in 100% of cases checked.
- **SC-005**: With a paid provider configured and no explicit permission, 100% of attempts to
  start an agent are refused, and no model call is made.
- **SC-006**: With the scripted model replaying the shortest solution, A2 succeeds with efficiency
  1.0 on 100% of the dev dungeons of all three levels.
- **SC-007**: For scripted episodes on at least 5 hand-built or generated dungeons, A2's map
  matches exactly what the tool results have revealed, in 100% of the steps before the one that
  ends the episode.
- **SC-008**: On the largest dev dungeon, fully explored, A2's rendered map takes less than a
  quarter of the model's context window.
- **SC-009**: The experimenter can go from opening the viewer to watching A1 or A2 play a chosen
  dungeon in under 30 seconds, without using the command line beyond starting the viewer.

## Assumptions

- **One user, one machine.** The viewer is a local tool for the experimenter alone: no accounts,
  no remote access. A current desktop browser is assumed.
- **The model** is the local `ollama:qwen3:8b` with the M2 settings (16,384-token context, 4,096
  output tokens per call), unless the experimenter changes it. Each model call takes about 9
  seconds, so an episode takes 1–5 minutes and live watching is the normal case.
- **One episode at a time**, because the local model serves one request well at a time.
- **Seeds:** watching dungeons and agents is development use. Dev seeds and seeds outside both
  sets are allowed. Test seeds are not, so they stay untouched for reported results
  (Constitution V).
- **Who writes A2:** the experimenter has asked the agent to write A2's graph (`mapstate`),
  including the map update and its rendering, as with A1. A2's map rendering and its instructions
  are part of A2, not shared setup. The base prompt and tool descriptions stay exactly as in M2,
  so the prompt fingerprint is unchanged.
- **Unchanged parts:** A1 and the command-line runner and report are unchanged, except that the
  runner accepts `mapstate`.
- **Out of scope:** comparing architectures with numbers, multi-episode runs from the page, and
  editing dungeons. The comparison is M4 (`docs/parked/m4-comparison/`).
- **No LLM judge:** the page shows what happened; it judges nothing.
