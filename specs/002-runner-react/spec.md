# Feature Specification: Runner, Results Format, Report and A1 ReAct

**Feature Branch**: `002-runner-react` (spec directory; no git branch is created)

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "M2 runner, results format, report and A1 ReAct"

## User Scenarios & Testing *(mandatory)*

The users of this feature are the experimenter, who plans, runs and reads experiments, and the
architectures, which play episodes. The experimenter writes the architecture graphs by hand
(constitution, Development Workflow). This feature provides everything around a graph: the
shared setup every architecture receives, the runner that plays episodes, the results files
and the report. A1 ReAct is the first graph to run through it.

### User Story 1 - Plan a run without spending anything (Priority: P1)

The experimenter describes a run: which architectures, which levels, which seed set (and
optionally which seeds from it), and how many repeats. Without `--execute`, the runner only
prints what it would do: the matrix, the number of episodes, the model and settings it would
use, and an upper bound on model calls, tokens and, if prices are configured, cost. Nothing is
sent to a model provider and nothing is written to the results folder.

**Why this priority**: Every paid run starts as a dry run, and the constitution requires it to
be the safe default (VI). It also checks the run description before money is at stake.

**Independent Test**: Run the planner for several run descriptions, with and without an API
key present and with the network unavailable, and compare the printed plan with hand-worked
counts. Confirm no request leaves the machine and no file is written.

**Acceptance Scenarios**:

1. **Given** the run "A1 on L2, dev seeds, 3 repeats" without `--execute`, **When** the
   experimenter starts it, **Then** the runner prints 30 planned episodes (10 seeds × 3
   repeats), the configured model and temperature, and upper bounds for model calls and
   tokens, and it makes no network request and writes no file.
2. **Given** a run description naming an unknown architecture, level or seed set, **When** the
   experimenter starts it, with or without `--execute`, **Then** it is refused with a message
   that lists the valid choices, and no episode starts.
3. **Given** prices per million input and output tokens in the configuration, **When** a dry
   run is printed, **Then** it also shows the worst-case cost of the run. Without prices it says
   that no cost estimate is available.
4. **Given** a run on the test seeds, **When** it is planned, **Then** the plan states that
   these results are for reporting, and a run on dev seeds states that its results are for
   development only.

---

### User Story 2 - Run episodes and record structured results (Priority: P2)

With `--execute`, the runner plays every episode in the matrix. For each one it generates the
dungeon, starts an episode, hands the architecture the four tools and the shared setup, and
lets it play until the episode ends. It writes one structured row per episode, keeps each
episode's full tool log and model conversation, and records the run's settings so the run can
be understood and compared later.

**Why this priority**: This produces the data every comparison rests on. It needs a working
architecture, which the tests provide with a scripted model, so it is testable without A1 and
without paid calls.

**Independent Test**: Run a small matrix with a scripted stand-in for the model (no paid calls)
and check every row against the episode's outcome record, the counted model calls and tokens,
and the saved settings.

**Acceptance Scenarios**:

1. **Given** a scripted model that replays a dungeon's shortest solution as tool calls,
   **When** the runner plays that episode, **Then** the row shows success, steps equal to the
   optimal steps, efficiency 1.0, no invalid actions, and model calls and tokens equal to what
   the scripted model reported.
2. **Given** a scripted model that stops calling tools before reaching the exit, **When** the
   episode is played, **Then** it ends as stopped, without costing a step, and the row shows
   failure.
3. **Given** a scripted model that keeps making tool calls, **When** the step budget runs out,
   **Then** the episode ends with the budget hit, and no further model call is made after the
   episode ended.
4. **Given** a scripted model whose token use passes the per-episode token cap, **When** the cap
   is passed, **Then** the episode ends as stopped, the row marks the token cap as hit, and no
   further model call is made.
5. **Given** a finished run, **When** the experimenter opens any episode's saved log with the
   existing map and animation, **Then** the route plays back exactly as the episode went.
6. **Given** a finished run, **When** its settings record is read, **Then** it contains the
   model, temperature, a fingerprint of the base prompt and tool descriptions, the token cap,
   the matrix, the seed set, the code version and whether the code had uncommitted changes.

---

### User Story 3 - Read a report (Priority: P3)

The experimenter turns one or more finished runs into a report: a table per architecture and
level with success rate, median efficiency, invalid actions, budget hits, model calls, tokens,
latency and the spread across repeats. The report says plainly whether it is built on dev or
test seeds and shows episodes that failed for infrastructure reasons separately.

**Why this priority**: The report answers the lab's question. It builds on the rows from
Story 2 and can be tested with hand-written rows.

**Independent Test**: Build reports from hand-written run folders with known numbers and check
every figure in the tables by hand.

**Acceptance Scenarios**:

1. **Given** a run folder with known rows, **When** the report is built, **Then** each
   architecture × level row shows the number of episodes, success rate, median efficiency over
   successful episodes, invalid actions per episode, budget-hit rate, token-cap-hit rate, median
   model calls, median input and output tokens and median latency, each matching a hand
   calculation.
2. **Given** a run with 3 repeats, **When** the report is built, **Then** it shows, for success
   rate and median efficiency, the lowest and highest value across the repeats.
3. **Given** two runs with the same model, temperature, prompt fingerprint, token cap and seeds
   but different architectures, **When** a report is built from both, **Then** both
   architectures appear in one table.
4. **Given** two runs whose model, temperature, prompt fingerprint or token cap differ, **When**
   a combined report is requested, **Then** it is refused with a message naming the differing
   settings.
5. **Given** a run that contains episodes marked as infrastructure errors, **When** the report is
   built, **Then** those episodes are left out of every score and listed in their own section
   with their error messages.
6. **Given** a run on dev seeds, **When** the report is built, **Then** it is headed as a
   development result that must not be reported.

---

### User Story 4 - Play A1 ReAct (Priority: P4)

The experimenter writes A1 ReAct by hand: the model calls tools in a loop and remembers only
through its message history. It plugs into the runner through the shared setup and is
selectable by name. A dry run and one small paid run on dev seeds produce a report.

**Why this priority**: It is the first real architecture and the baseline for every later one.
It comes last because the graph is written by the experimenter, on top of Stories 1–3.

**Independent Test**: Play A1 with a scripted model that replays the shortest solution, so the
graph's wiring is checked without paid calls. Then do one small paid run and build its report.

**Acceptance Scenarios**:

1. **Given** A1 and a scripted model that replays the shortest solution as tool calls, **When**
   the runner plays an L1, L2 and L3 dev dungeon, **Then** every episode succeeds in the optimal
   number of steps.
2. **Given** A1 and a scripted model that answers in plain text without a tool call, **When** the
   episode is played, **Then** A1 finishes and the episode ends as stopped.
3. **Given** the run "A1 on L1–L3, 2 dev seeds, 1 repeat" with `--execute` and the API key set,
   **When** the experimenter runs it, **Then** 6 rows are written and a report is built from
   them.
4. **Given** the architecture source files, **When** the boundary checks run, **Then** A1 uses
   only the four tools, the agent-facing results and the shared setup, and it creates no model
   of its own.

---

### Edge Cases

- `--execute` without an API key for the configured provider: the run is refused before any
  episode starts, with a message naming the missing setting.
- The provider fails with a rate limit, timeout or server error: the call is retried a small,
  fixed number of times with a growing pause. If it still fails, the episode is recorded as an
  infrastructure error with the message, and the run moves on to the next episode.
- The provider rejects a request permanently (for example an invalid key or an unknown model):
  the run stops at once instead of failing every remaining episode the same way. Rows already
  written are kept.
- The model calls a tool that does not exist, or calls one of the four with missing or malformed
  arguments: the call is answered with a structured error, counts as one step and as an invalid
  action.
- The model makes several tool calls in one turn: they are carried out in order, each counts as
  one step, and calls after the episode has ended are not carried out.
- The provider reports no token usage for a call: the token fields are recorded as unknown, not
  as zero, and the report says how many episodes lack token data.
- The configured model does not accept a temperature setting: the run records that the
  provider's default was used. This is the same for every architecture in the run, so the
  conditions stay identical.
- A run is interrupted (for example with Ctrl-C): rows of finished episodes are kept, the
  settings record marks the run as incomplete, and the report says so.
- A seed selection asks for more seeds than the set has, or for seeds that are not in the set:
  it is refused with a clear message.
- The results folder for a new run already exists: the runner never overwrites it. Each run gets
  its own new folder.
- A report is requested for a folder that is not a run, or whose rows do not match the expected
  format: it is refused with a clear message.

## Requirements *(mandatory)*

### Functional Requirements

**Shared setup (constitution I and III)**

- **FR-001**: There MUST be one shared configuration for a run: the model, the temperature, the
  base prompt, the tool descriptions, the per-episode token cap and the retry policy. The model
  is named by `APL_MODEL`. Every architecture in a run MUST receive the same values, and an
  architecture MUST NOT be able to change them.
- **FR-002**: The runner MUST hand each architecture, per episode, the four tools for that
  episode, the free start-room description, and the shared setup: a ready model, the base prompt
  and the tool descriptions. Architectures MUST use that model and MUST NOT create one of their
  own.
- **FR-003**: The tools handed to an architecture MUST pass every call to the episode, so that
  every tool call counts as one step, including invalid calls, calls with malformed arguments
  and calls to tools that do not exist. Tool results MUST reach the model as the structured
  results defined in M1.
- **FR-004**: The base prompt MUST tell the model its goal (reach the exit), the rules (one step
  per tool call, a step budget), and how tool results are structured. It MUST NOT reveal the
  budget's value, the shortest solution or anything about the layout. Architectures add their
  node-specific instructions on top of it, never in place of it.
- **FR-005**: The tool descriptions MUST describe the four tools, their arguments and their
  possible errors, and MUST be the same for every architecture.

**Architectures**

- **FR-006**: Architectures MUST be selectable by a short name (A1 is `react`). The runner MUST
  list the registered names when an unknown one is given.
- **FR-007**: An architecture MUST be a graph that plays one episode: it receives what FR-002
  lists and returns when it is done. The runner, not the architecture, decides how the episode
  ended.
- **FR-008**: When an architecture returns before the episode has ended, the runner MUST end the
  episode as stopped. That MUST NOT cost a step.
- **FR-009**: Once the episode has ended (exit reached, budget used up, or token cap passed), the
  runner MUST NOT make any further model call for that episode.
- **FR-010**: The existing boundary check MUST cover the architectures and MUST also confirm that
  they create no model of their own and import nothing beyond the four tools, the agent-facing
  results and the shared setup.
- **FR-011**: A1 ReAct MUST call tools in a loop driven by the model, with the message history as
  its only memory, and MUST finish when the model answers without a tool call or the episode
  ends. The experimenter writes A1's graph; this feature provides everything it plugs into.

**Runner**

- **FR-012**: A run MUST be described by: one or more architectures, one or more levels, a seed
  set (dev or test) with an optional selection (the first k seeds, or a list of seeds from the
  set), and a number of repeats. The matrix is every combination.
- **FR-013**: Without `--execute`, the runner MUST print the plan and do nothing else: the matrix,
  the number of episodes, the model, the temperature, the token cap, which seed set is used and
  what that means for reporting (FR-030), an upper bound on model calls (the sum of the episodes'
  step budgets plus one per episode), and an upper bound on tokens (episodes × per-episode token
  cap). If prices per million input and output tokens are
  configured, it MUST also print the worst-case cost. It MUST NOT contact a model provider or
  write any file.
- **FR-014**: With `--execute`, the runner MUST first check that the provider's API key is
  configured and refuse to start otherwise. It MUST then play the episodes one after another
  and write each row as soon as its episode finishes.
- **FR-015**: Each run MUST be written to a new folder under `results/`, named by a run id that
  includes the start time. An existing folder MUST NOT be overwritten.
- **FR-016**: The runner MUST stop an episode once its token use passes the per-episode token cap
  (plan §8), end it as stopped, and mark the row as token cap hit.
- **FR-017**: The runner MUST retry a failed model call on a rate limit, timeout or server error a
  fixed number of times with a growing pause. If it keeps failing, the episode MUST be recorded
  as an infrastructure error and the run MUST continue. A permanent rejection (invalid key,
  unknown model) MUST stop the run.
- **FR-018**: If a run is interrupted, the rows already written MUST be kept and the settings
  record MUST mark the run as incomplete.

**Results format (constitution IV)**

- **FR-019**: Each run folder MUST contain a settings record, an episodes file with one row per
  episode, and per-episode files with the tool log and the model conversation.
- **FR-020**: The settings record MUST hold: run id, start and end time, whether the run
  completed, the architectures, levels, seed set and seeds, repeats, model, temperature (or
  "provider default"), the token cap, a fingerprint of the base prompt and tool descriptions,
  the code version, whether the code had uncommitted changes, and the versions of the main
  libraries.
- **FR-021**: Each episode row MUST hold: run id, architecture, level, seed, seed set, repeat
  number, status (`completed` or `error`), success, end reason, steps, optimal steps, budget,
  efficiency, invalid actions, budget hit, token cap hit, model calls, tool calls, input tokens,
  output tokens and latency in seconds. An `error` row MUST also hold the error message.
- **FR-022**: Efficiency MUST be optimal steps divided by steps for a successful episode, so 1.0
  is perfect, and MUST be empty for a failed one. Tool calls MUST count every call the
  architecture made, including uncounted calls after the episode ended. Latency MUST be the wall
  time of the whole episode.
- **FR-023**: Model calls and token counts MUST be measured by the runner for every architecture
  in the same way, from what the provider reports. Missing token data MUST be recorded as
  unknown, not as zero.
- **FR-024**: Each episode's tool log MUST be saved in the M1 outcome-record format, so that the
  existing `apl dungeon show --route` can draw and animate it.
- **FR-025**: Each episode's model conversation MUST be saved as it was sent and received:
  messages, tool calls, tool results and token use per call.

**Report (constitution IV and V)**

- **FR-026**: `apl report` MUST build a report from one or more run folders and write it as a
  markdown file, as well as printing it.
- **FR-027**: For each architecture × level, the report MUST show: completed episodes, success
  rate, median efficiency over successful episodes, invalid actions per episode, budget-hit rate,
  token-cap-hit rate, median model calls, median input and output tokens, and median latency.
- **FR-028**: When a run has more than one repeat, the report MUST show the lowest and highest
  success rate and median efficiency across repeats, where each repeat's value is computed over
  its seeds.
- **FR-029**: Infrastructure-error episodes MUST be left out of every score and listed in their
  own section, with architecture, level, seed, repeat and error message. Episodes without token
  data MUST be counted in a note.
- **FR-030**: The report MUST state whether it is built on dev or test seeds. A dev-seed report
  MUST be headed as a development result that must not be reported. Runs on different seed sets
  MUST NOT be combined.
- **FR-031**: The report MUST refuse to combine runs whose model, temperature, prompt fingerprint
  or token cap differ, and MUST name the settings that differ. It MUST also say when the combined
  runs did not all use the same seeds.
- **FR-032**: Reports MUST be computed by code from the rows alone. No model is involved.

**Safety (constitution VI)**

- **FR-033**: No code path may make a paid model call without `--execute`. Tests MUST NOT make
  paid calls; they use a scripted stand-in for the model.

### Key Entities

- **Shared setup**: The run-wide values every architecture receives: model, temperature, base
  prompt, tool descriptions, token cap and retry policy, plus a fingerprint of the prompt and
  tool descriptions.
- **Architecture**: A named graph that plays one episode with the tools and the shared setup.
- **Run description**: Architectures, levels, seed set and selection, repeats, and whether to
  execute.
- **Run**: One execution of a run description, stored in its own folder with a settings record,
  episode rows and per-episode files.
- **Settings record**: Everything needed to understand and compare a run later (FR-020).
- **Episode row**: The scored summary of one episode (FR-021).
- **Episode files**: The tool log in the M1 outcome format, and the model conversation.
- **Report**: Tables per architecture and level, built by code from one or more compatible runs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A dry run makes no network request and writes no file in 100% of tested cases,
  including with a valid API key present, and its episode count matches the hand-worked count
  for every tested run description.
- **SC-002**: With the scripted model replaying the shortest solution, 100% of episodes on all
  dev dungeons of all three levels succeed with efficiency 1.0, and the recorded steps, model
  calls and tokens match what the scripted model did.
- **SC-003**: In 100% of tested episodes, no model call is made after the episode ended, whether
  it ended at the exit, by the budget or by the token cap.
- **SC-004**: Every saved episode log replays through the existing map and animation to the same
  end, step and end reason as its row, in 100% of tested episodes.
- **SC-005**: Every figure in a report built from hand-written runs matches a hand calculation,
  including the spread across repeats and the exclusion of error episodes.
- **SC-006**: Combining runs with differing model, temperature, prompt fingerprint, token cap or
  seed set is refused in 100% of tested combinations.
- **SC-007**: The boundary check fails for an architecture file that creates its own model or
  imports environment internals, and passes for A1.
- **SC-008**: A1 with the scripted model succeeds in the optimal number of steps on one dev
  dungeon of each level.
- **SC-009**: One dry run and one small paid run (A1 on L1–L3, 2 dev seeds, 1 repeat: 6 episodes)
  both complete, and a report is built from the paid run (plan.md M2).
- **SC-010**: The runner adds less than 1 second of overhead per episode beyond the model's own
  response time, measured with the scripted model.

## Assumptions

- The default model is `openai:gpt-6-luna` on the OpenAI API, with its key in `.env`
  (plan.md §9). Any provider the model setting can name works the same way.
- The subscription gateway is not used in this feature: every model call here needs tool calls,
  which the gateway rejects, and experiment episodes must call the raw model (plan.md §9).
- The experimenter writes A1's graph. This feature specifies its behavior, the interface it
  plugs into and the tests it must pass, and the implementation pauses for the experimenter at
  that task.
- The base prompt and the tool descriptions are shared setup, not graph logic, so they are
  written as part of this feature. The experimenter can revise them before any reported run;
  changing them changes the fingerprint, which keeps old and new runs apart.
- The per-episode token cap and the retry policy have sensible defaults in the shared
  configuration. Exact values are chosen in the plan.
- Episodes run one after another. Running several at once can come later if runs get slow.
- An interrupted run is not resumed. A new run is started instead.
- Prices are optional configuration entered by the experimenter. The runner never looks them up.
- The small paid run in SC-009 is started by the experimenter, or by an agent only after the
  experimenter has explicitly approved that run.
- The upper bound on model calls assumes at most one model call per step plus one final call per
  episode. Architectures with several model calls per step (later milestones) may raise it.
- Tracing (for example Langfuse) is out of scope here and may come later.
