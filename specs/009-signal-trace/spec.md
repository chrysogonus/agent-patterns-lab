# Feature Specification: The Signal Trace

**Feature Branch**: `009-signal-trace` (spec directory; no git branch is created)

**Created**: 2026-11-02

**Status**: Draft

**Input**: User description: "M9, feature 009: the signal trace, the lab's third problem (plan.md §9
lists it among the problem mock-ups; visual mock-up: https://claude.ai/artifact/VEDrZX6TuFapmV4rHkTCqB,
section "Signal trace"). Water flows from a source S through a pipe of N segments, and exactly one
segment is broken; water reaches every segment before the break and none after it. The agent finds
the broken segment with probe(segment), which says whether water reaches that segment and costs one
step, and ends the episode with submit(segment). Scored by code: success when the submitted segment
is the broken one, probes used against a reference (bisection, about log2 N probes), invalid
actions, calls, tokens. The property this board is built to show: the model is never misled here,
only short-sighted; the gap comes from choosing the next probe, so A6 hybrid (code keeps the set of
suspect segments from earlier probe results) should need about log2 N probes where A1 ReAct needs
about N. Levels grow the pipe and later make it harder (branching pipes, or probes that are
sometimes wrong), so planning (A3) has to reason about how much each probe tells it. It plugs into
the multi-problem support built in M5 exactly like the survey field: its own tools, level ladder,
seeds, scoring and step budget; the fairness rules (same model, prompt, tool descriptions and
budget; world access only through the problem's tools; structured results; dev vs test seeds; no
paid call without --execute) apply within the problem; the constitution's tool rule is amended to
name the new tools; the dungeon and the survey field stay unchanged. apl run, apl continue, apl
report and apl serve take it as a problem; the viewer shows the pipe, the probed segments (wet or
dry), the suspect band narrowing, and the submitted segment next to the true one. Architectures that
already exist are made to play it where they make sense. Done when: any signal-trace level and seed
can be shown and watched in the viewer, signal-trace runs plan, continue and report like dungeon and
survey runs, and the existing problems are unchanged. No paid or local experiment runs are started
as part of this work unless explicitly requested."

## Clarifications

### Session 2026-11-02

- Q: Which step budget rule? → A: The larger of 3× the reference and a full probe-by-probe scan
  (N−1 probes, submit), so every architecture can finish and the gap shows in probes and
  efficiency.
- Q: What makes T3 harder than T2? → A: Branching pipes: 64 segments in a tree. Probes stay always
  true on every level.
- Q: Who writes the signal-trace versions of A1–A4 and A6 in `src/apl/arch/`? → A: The agent, at
  the experimenter's request, as in M5–M8; the experimenter reviews them afterwards.

## User Scenarios & Testing *(mandatory)*

The user of this feature is the experimenter. The dungeon (M4) showed little difference between
most architectures, and the survey field (M5) was built to show one property: splitting the work.
The signal trace is built to show another: choosing what to look at next. Every probe answer is
true and easy to read, so a model can never be misled; it can only waste probes. An agent that
tests segment after segment needs about N probes, one that halves the suspects every time needs
about log₂ N. Code doing the bookkeeping (A6) should halve them; a model working from its history
alone (A1) may not.

The signal trace in one paragraph: water flows from a source S through a pipe made of numbered
segments. Exactly one segment is broken. Water reaches every segment upstream of the break; the
broken segment and everything downstream of it stay dry. The agent sees the layout of the pipe,
probes segments one at a time to learn whether each is wet or dry, and finally submits the segment
it thinks is broken. The episode is a success when it names the right one.

Architectures in this feature:

| Name | Architecture | On the dungeon and the survey field | On the signal trace |
| --- | --- | --- | --- |
| `react` | A1 ReAct | as before | yes |
| `mapstate` | A2 map state | as before | yes, with a probe log in state (answers kept, nothing inferred) |
| `plan_execute` | A3 plan-and-execute | as before | yes |
| `reflexion` | A4 Reflexion | as before | yes, a wrong submission ends an attempt while attempts are left |
| `hybrid` | A6 hybrid | as before (dungeon only) | yes: code keeps the suspect set from the probe answers, the model picks the next probe |
| `mapstate_routes`, `supervisor`, `fanout`, `rounds`, `blackboard` | A2r, A5, A7–A9 | as before | no |

### User Story 1 - Watch an architecture trace a pipe (Priority: P1)

In the viewer, the experimenter picks the signal trace, a level and a dev seed, and sees the pipe.
They pick an architecture and press Run. Every probe appears on the pipe as it happens: the probed
segment turns wet or dry, the water line fills up to the furthest wet segment, and the segments
still suspect stay shaded, so the suspect band can be watched shrinking. A panel shows the probes
used against the reference, the suspects left, and, at the end, the submitted segment next to the
broken one, marked right or wrong. The side panel shows each model turn as it does for the other
problems. Episodes are saved and can be replayed.

**Why this priority**: Watching the band halve, or shrink one segment at a time, is the point of
the board. It needs the problem itself (US2) and is the first thing the experimenter will use.

**Independent Test**: Start the viewer, open the signal trace T1 seed 1000, play a scripted agent
that bisects and submits the right segment, and check that the wet and dry marks, the suspect count,
the submitted segment and the replay all match the saved events.

**Acceptance Scenarios**:

1. **Given** the viewer is open, **When** the experimenter picks the signal trace, level T1 and seed
   1000, **Then** the pipe is shown with its broken segment marked, and with "Agent's view" on, the
   break is hidden and every segment is suspect.
2. **Given** an episode is running, **When** the agent probes a segment, **Then** that segment is
   marked wet or dry, and the suspect band shrinks to the segments still consistent with all
   answers so far.
3. **Given** an episode ends with a submission, **When** the experimenter looks at the panel,
   **Then** it shows the submitted segment next to the broken one, marked right or wrong, and the
   probes used against the reference.
4. **Given** an architecture that does not play the signal trace, **When** the experimenter looks
   at the architecture list for this problem, **Then** it cannot be chosen.
5. **Given** a test seed, **When** the experimenter enters it, **Then** the viewer refuses it, as
   it does for the other problems.

---

### User Story 2 - The signal-trace problem (Priority: P1)

A seed and a level always build the same pipe with the same broken segment. The agent acts only
through the signal trace's tools, each call costs one step, and errors are structured like the
other problems'. Every pipe has a reference computed by code, which sets the step budget and the
efficiency score.

**Why this priority**: Without it there is nothing to watch or compare. It is listed second only
because it is invisible on its own.

**Independent Test**: Generate pipes for every level and dev and test seed, check the layout and
the single break, play scripted probe sequences against the tools and check every answer, and check
that a seeded pipe is identical across runs.

**Acceptance Scenarios**:

1. **Given** a pipe, **When** an episode starts, **Then** the agent is given the layout free, as
   the other problems give their start view: every segment and the segment it is fed from. `look`
   returns the same layout again for one step.
2. **Given** a pipe, **When** the agent probes a segment upstream of the break, **Then** the answer
   is wet; **When** it probes the broken segment or one downstream of it, **Then** the answer is dry.
3. **Given** the agent probes a segment that does not exist, **When** the call returns, **Then** it
   fails with a structured error and costs a step.
4. **Given** the agent submits a segment, **When** the call returns, **Then** the episode ends, and
   it is a success exactly when that segment is the broken one.
5. **Given** the step budget is used up without a submission, **When** the episode ends, **Then** it
   is a failure, marked as out of budget.

---

### User Story 3 - Run, continue and report on the signal trace (Priority: P2)

The experimenter plans and runs signal-trace episodes with the same commands as for the other
problems, naming the problem. The plan is free and shows the matrix and an estimate; `--execute`
plays it. An interrupted run can be continued. The report adds the signal trace's own columns:
how often the submitted segment was right, how many probes were used against the reference, and
how many probes were wasted, meaning their answer was already implied by earlier answers.

**Why this priority**: The viewer shows the difference on one seed. A run with repeats is how the
experimenter checks whether it holds across seeds.

**Independent Test**: Plan a signal-trace run without `--execute` and check the matrix; play a run
with scripted architectures, interrupt it, continue it, and check the report against the rows.

**Acceptance Scenarios**:

1. **Given** the signal trace is named, **When** the experimenter plans a run without `--execute`,
   **Then** the plan shows the signal-trace levels, seeds, architectures and an estimate, and no
   model is called.
2. **Given** a signal-trace run names an architecture that does not play it, **When** it is
   planned, **Then** it is refused with a message that names the architecture and the problem.
3. **Given** an interrupted signal-trace run, **When** the experimenter continues it, **Then** only
   the missing episodes are planned, as for the other problems.
4. **Given** a completed signal-trace run, **When** the report is written, **Then** it shows, per
   architecture and level, the share of right submissions, median probes, median efficiency, median
   wasted probes, budget hits, tokens and latency, with the spread across repeats, and the
   comparison section.

---

### User Story 4 - The fairness rules hold on the signal trace (Priority: P2)

Within the signal trace every architecture gets the same model, base prompt, tool descriptions and
step budget, and reaches the pipe only through its tools. The broken segment is never visible to an
architecture except through probe answers. Results from the signal trace are never combined with
results from another problem.

**Why this priority**: The lab's results mean nothing if the rules are not checked. The import test
and the recorded fingerprints must cover the new problem.

**Independent Test**: The test that limits what architectures may import passes with the signal
trace's public tool and result definitions added, and fails for an architecture that reads the
pipe's generator or its broken segment.

**Acceptance Scenarios**:

1. **Given** the constitution, **When** this feature is done, **Then** principle II names the
   signal trace's tools, the Experiment Setup describes its pipes, reference and budget, and the
   version and amendment date are updated.
2. **Given** an architecture that imports the signal trace's generator, **When** the tests run,
   **Then** the import test fails.
3. **Given** two architectures on the same signal-trace level, **When** their episodes run,
   **Then** both got the same base prompt, tool descriptions and step budget, as recorded in the
   results.

---

### Edge Cases

- The broken segment is the first one: every probe is dry; the agent can still find it.
- The broken segment is the last one on a line: every probe upstream is wet.
- The agent probes the same segment twice: the answer is the same, the call costs a step, and it
  counts as a wasted probe.
- The agent probes a segment whose answer is already implied (downstream of a known dry segment, or
  upstream of a known wet one): the answer is still given and still costs a step; it counts as a
  wasted probe.
- The agent submits without probing at all: the episode ends with that segment, scored right or
  wrong like any other.
- The agent probes or submits something that is not a segment (a name outside the pipe, not a
  number, the source S): the call fails with a structured error, costs a step, and the episode goes
  on.
- A model reply has no tool call and no submission: the episode ends as a failure without a
  submission, marked as given up, as on the other problems.
- A4 submits a wrong segment while attempts are left: the attempt ends with a result that says only
  that the segment was wrong; the pipe restarts unchanged; every step of every attempt counts toward
  the one budget, and the episode is scored on the last submission.
- On a branching pipe, a dry answer on one branch says nothing about segments on other branches;
  the suspect set follows the layout, not the numbering.
- Dungeon and survey runs, reports and saved episodes from before this feature still load, continue
  and report as before.

## Requirements *(mandatory)*

### Functional Requirements

**The signal trace**

- **FR-001**: The signal trace MUST be a third problem next to the dungeon and the survey field,
  with its own tools and their descriptions, base prompt, levels, dev and test seeds, reference,
  scoring and step budget rule.
- **FR-002**: A pipe MUST be generated from a level and a seed, identical every time for the same
  pair. It MUST consist of numbered segments fed from a source S, where every segment is fed from S
  or from exactly one other segment, and exactly one segment MUST be broken.
- **FR-003**: Water MUST reach a segment exactly when no segment on its path from S (itself
  included) is broken.
- **FR-004**: The signal trace MUST have three levels:

  | Level | Segments | Layout | Purpose |
  | --- | --- | --- | --- |
  | T1 | 16 | one straight line | Baseline; every architecture should find the break |
  | T2 | 64 | one straight line | About 6 probes for bisection against about 32 on average for a probe-by-probe scan |
  | T3 | 64 | branching: a tree with 4 pipe ends, where a segment feeds at most two others | A dry answer cuts off one branch only, so the best probe is no longer halfway along the numbers |

- **FR-005**: Agents MUST act only through these tools, each call costing one step, failed calls
  included:

  | Tool | Returns |
  | --- | --- |
  | `look()` | The layout again: every segment's number and the segment (or S) it is fed from |
  | `probe(segment)` | Whether water reaches that segment (wet or dry), or an error (no such segment) |
  | `submit(segment)` | Ends the episode naming that segment as broken, or an error (no such segment) |

  The layout is also given free at the start of the episode, as the other problems give their
  start view, so an agent never needs `look` to begin.

- **FR-006**: Results and errors MUST be structured data with the same shape as the other problems'
  (`ok`, `error` with `code` and `message`, `data`). A probe answer MUST be true and deterministic:
  the same segment always gives the same answer within an episode.
- **FR-007**: An episode MUST end when a submission is made (for A4, when a wrong submission comes
  with no attempt left), when the step budget is used up, or when the architecture stops without
  submitting. It MUST be a success exactly when the submitted segment is the broken one.
- **FR-008**: Code MUST compute a reference for every pipe: the worst-case number of probes of
  code's own probe strategy on that layout, plus one submission. On straight levels the
  strategy MUST be bisection, whose worst case (⌈log₂ N⌉ probes) is the optimum; on any other level
  the results MUST say the reference is not proven optimal.
- **FR-009**: The step budget MUST be the larger of 3× the reference and a full probe-by-probe
  scan (N−1 probes and one submission): 16 on T1, 64 on T2 and on T3 (whose trees keep the
  reference at about 8 steps, research R4). Every architecture can
  then finish, and the gap shows in probes and efficiency rather than in budget hits.
- **FR-010**: A retrying architecture (A4) MUST be able to restart the pipe up to 3 attempts per
  episode, as on the other problems: a restart costs no step, the pipe and its break are unchanged,
  and all attempts share one budget.

**Runner and report**

- **FR-011**: `apl run` MUST accept the signal trace as a problem; `apl continue` and `apl report`
  MUST take it from the run. A show command MUST print a pipe for a level and seed, with an option
  to show the reference probes. Without `--execute`, no model is called (constitution VI).
- **FR-012**: Each signal-trace result row MUST record, besides the fields every episode records:
  the submitted segment (or none), the broken segment, the number of segments, the probes, and the
  wasted probes.
- **FR-013**: A probe MUST count as wasted when its answer was already implied by the answers to
  earlier probes in the same attempt, including a repeat of an earlier probe.
- **FR-014**: The signal-trace report MUST show per architecture and level: the share of right
  submissions, median probes, median efficiency (steps against the reference), median wasted
  probes, budget hits, tokens and latency, with the spread across repeats, and the comparison
  section M4 introduced.

**Viewer**

- **FR-015**: The viewer MUST offer the signal trace as a problem; its levels, seeds and the
  architectures that play it MUST follow from that choice.
- **FR-016**: For the signal trace, the viewer MUST draw the pipe's layout, each probed segment as
  wet or dry, the water reaching the furthest known wet segments, the segments still suspect, the
  broken segment unless "Agent's view" hides it, and a panel with probes against the reference,
  suspects left, wasted probes, and the submitted segment marked right or wrong.
- **FR-017**: The step slider, replay of saved episodes and the side panel of model turns MUST work
  for the signal trace as for the other problems.

**Rules**

- **FR-018**: The constitution MUST be amended: principle II names the signal trace's tools and
  forbids reading the broken segment; the Experiment Setup gains the signal trace's generation,
  reference and budget; the attempt rule covers a wrong submission on the signal trace.
- **FR-019**: Architectures MUST be allowed to import only the shared kit and each problem's public
  tool and result definitions; the import test MUST enforce this for the signal trace.
- **FR-020**: The dungeon and the survey field MUST behave exactly as before: same worlds per seed,
  tools, prompts, budgets, scoring and results format.

**Architectures**

- **FR-021**: A1 (`react`) MUST play the signal trace with its base prompt and tools and nothing
  else changed.
- **FR-022**: A2 (`mapstate`) MUST play the signal trace with a probe log in its state, rendered
  each turn: the answers so far, with no inference drawn from them.
- **FR-023**: A3 (`plan_execute`) and A4 (`reflexion`) MUST play the signal trace with the same
  probe log as A2, since both build on A2's memory; A4 reflects after a wrong submission as it does
  after a wrong total on the survey field.
- **FR-024**: A6 (`hybrid`) MUST play the signal trace with code that keeps the suspect set from the
  probe answers and shows which probes would split it most evenly; the model picks the next probe
  or the submission. Code MUST work only with what earlier tool results revealed.
- **FR-025**: The agent writes the signal-trace versions of A1–A4 and A6 in `src/apl/arch/`, at
  the experimenter's request; the experimenter reviews them afterwards. Their behavior on the other
  problems MUST NOT change.

### Key Entities

- **Pipe**: a layout of numbered segments fed from a source S, generated from a level and a seed,
  with one broken segment, a reference and a step budget.
- **Segment**: a numbered piece of pipe with the segment (or S) it is fed from; wet or dry
  depending on where the break is.
- **Probe answer**: the result of one probe: the segment and whether it is wet.
- **Suspect set**: the segments still consistent with every probe answer so far; computed by the
  viewer, the report and A6's code from answers alone.
- **Signal-trace outcome**: the result of one episode: success, submitted segment, broken segment,
  probes, wasted probes, steps, budget hit, and the fields every episode records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every dungeon and survey command from before this feature produces the same output,
  and every existing test passes without changes to what it checks.
- **SC-002**: For every signal-trace level and every dev and test seed, the generated pipe is
  identical across runs, has the level's number of segments, and has exactly one broken segment.
- **SC-003**: A scripted agent that follows the reference strategy and submits the segment it finds
  succeeds on every level and seed within the reference step count.
- **SC-004**: Averaged over all T2 dev and test seeds, a scripted probe-by-probe agent uses at
  least three times as many probes as the reference, so the gap the board is built to show exists
  by construction.
- **SC-005**: In the viewer, the experimenter can go from opening the page to watching a T2 episode
  in under a minute, and can replay it afterwards step by step.
- **SC-006**: Every signal-trace tool result, error and outcome in a saved episode can be checked
  by code against the pipe, with no free-text parsing; the wasted-probe count is reproduced from the
  saved answers alone.
- **SC-007**: A dry-run plan for the signal trace never calls a model, and the tests never make a
  paid call.

## Assumptions

- Problem name `signal`, levels T1–T3; the seed numbers are the other problems' (dev 1000–1009, test
  2000–2019), keyed by the problem name, so the pipes are unrelated to the other worlds.
- The layout is public and given free at the start, because the board tests the choice of probe,
  not exploration. `look()` repeats it for one step, like every tool call (constitution III), for an
  agent that has lost it; the reference does not need it.
- The broken segment is drawn uniformly from all segments, so a probe-by-probe scan from the source
  needs about N/2 probes on average and N−1 in the worst case.
- Probes are never wrong, on any level. Noisy probes are left for a later level or feature.
- A7–A9 are left out: a pipe has no regions to walk, so scouts would only split probes, which is
  not the property this board shows. A2r and A5 are left out because the signal trace has no routes
  and no items.
- A4's 3 attempts mean it may submit up to three times, as it may on the survey field; the report
  shows this through its success share and steps, as it does there.
- This feature includes no paid or local experiment run. Running a comparison and writing findings
  is the experimenter's choice afterwards, with the commands from US3.
- The constitution amendment adds a problem without changing a principle's meaning, so it is a
  MINOR version (2.2.0), made with `/speckit-constitution` before this feature's plan.
- The visual mock-up linked in the input shows intended behavior; its numbers are illustrative.
