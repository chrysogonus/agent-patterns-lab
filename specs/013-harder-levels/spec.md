# Feature Specification: Harder Top Levels for the Signal Trace and the Workshop

**Feature Branch**: `013-harder-levels` (spec directory; work happens on git branch
`m13-harder-levels`)

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: empty `/speckit-specify`, taken as the M13 the experimenter was
offered after the first `openai:gpt-6-luna` run on the four new problems (2026-11-03): "M13:
harder top levels where the boards saturate. A T4 for signal (more suspects, or the noisy probes
plan.md deferred) and a W4 for workshop (a scarcer material, deeper recipes), with the generators,
tests and viewer updated. Same shape as earlier problem milestones, but smaller."

## User Scenarios & Testing *(mandatory)*

The user of this feature is the experimenter. The 2026-11-03 run (one dev seed per level,
`openai:gpt-6-luna`) showed that two boards no longer tell the architectures apart:

- **Signal trace:** every architecture found the broken segment on T1–T3, nearly all with
  efficiency 1.00 and no wasted probe.
- **Workshop:** every architecture crafted the goal on W1–W3 except one (hybrid stuck on W3), with
  efficiency between 0.84 and 1.00.

A board on which every architecture scores the same answers nothing. This feature adds one harder
level at the top of each ladder, built by the same rules as the levels below it, so the next
comparison (M14) has a level on each board where the architectures can still differ. It adds no
new board, tool or architecture, and it changes nothing about the existing levels.

The two new levels:

| Level | Board | Size | What gets harder |
| --- | --- | --- | --- |
| T4 | Signal trace | 256 segments, a tree with 8 pipe ends, every run at least 4 segments | Four times T3's segments and twice its branches: many more runs to weigh when choosing the probe that splits the suspects best |
| W4 | Workshop | 12 craftable items, 5 levels deep, 3 conflicts | Three scarce materials a plan must protect at once, one level deeper than W3 |

### User Story 1 - Show and watch a T4 pipe (Priority: P1)

The experimenter picks the signal trace, level T4 and a dev seed in the viewer and sees the pipe:
256 segments in their runs, with S, the branch points and the 8 pipe ends readable. They pick an
architecture that plays the signal trace and press Run; every probe appears as it happens, as on
T1–T3. From the command line, `apl signal show --level T4 --seed <n>` draws the same pipe, with the
reference route when asked.

**Why this priority**: T4 is the reason for the feature on the signal board; without it being
shown and played, nothing else in the feature can be checked by eye.

**Independent Test**: Generate T4 for every dev and test seed and check the level's shape, its
reference and its budget; open T4 seed 1000 in the viewer and in `apl signal show`.

**Acceptance Scenarios**:

1. **Given** level T4 and any dev or test seed, **When** the pipe is generated twice, **Then** both
   pipes are identical, with 256 segments, 8 pipe ends, no run shorter than 4 segments, no segment
   feeding more than two others, and exactly one broken segment.
2. **Given** a T4 pipe, **When** code's own probe strategy plays it for every possible broken
   segment, **Then** it always submits the broken segment within the reference steps, and the
   reference is marked as a reference, not an optimum (the layout is a tree).
3. **Given** a T4 pipe, **When** its budget is computed, **Then** it is the larger of 3× the
   reference steps and a full probe-by-probe scan (255 probes and the submission), as on T1–T3.
4. **Given** the viewer on the signal trace, **When** the level list is opened, **Then** it offers
   T1, T2, T3 and T4, and T4 seed 1000 can be shown and played live and replayed afterwards.

---

### User Story 2 - Show and watch a W4 workshop (Priority: P1)

The experimenter picks the workshop, level W4 and a dev seed in the viewer and sees the recipe
tree: the goal, 12 craftable items over 5 levels, the three tempting items with their two recipes,
and the stock with its three scarce materials. They pick an architecture that plays the workshop
and press Run; every inspect, gather and craft appears as it happens, as on W1–W3. From the
command line, `apl workshop show --level W4 --seed <n>` draws the same workshop, with the reference
plan when asked.

**Why this priority**: W4 is the reason for the feature on the workshop board, and it is
independent of T4: either can be built, shown and played without the other.

**Independent Test**: Generate W4 for every dev and test seed and check its shape, that its
reference plan crafts the goal, and that taking every first-listed recipe gets stuck; open W4 seed
1000 in the viewer and in `apl workshop show`.

**Acceptance Scenarios**:

1. **Given** level W4 and any dev or test seed, **When** the workshop is generated twice, **Then**
   both are identical, with 12 craftable items under the goal, 5 levels of craftables counting the
   goal, 3 tempting items with two recipes, and 3 scarce raw materials with a stock of 1 each.
2. **Given** a W4 workshop, **When** the reference plan is played, **Then** it crafts the goal in
   exactly the reference steps, and the budget is 3× the reference.
3. **Given** a W4 workshop, **When** a plan always takes each item's first-listed recipe, **Then**
   the episode ends as stuck before the goal is crafted.
4. **Given** the viewer on the workshop, **When** the level list is opened, **Then** it offers W1,
   W2, W3 and W4, and W4 seed 1000 can be shown and played live and replayed afterwards.

---

### User Story 3 - Run, continue and report the new levels (Priority: P2)

The experimenter plans a signal or workshop run with `--level all` and sees T4 or W4 in the episode
matrix and in the dry run's upper bounds. They can also pick the new level alone
(`--level T4`, `--level W4`). An interrupted run with a new level continues like any other, and the
report shows the new level in its tables and comparisons. Earlier runs, made when `all` meant three
levels, still continue and report as they did.

**Why this priority**: The levels exist to be compared; but showing and watching them (US1, US2)
already proves they work, so running them at scale can follow.

**Independent Test**: Dry-run `apl run --problem signal --arch react --level all --seeds dev
--limit 1` and the workshop equivalent and check the matrix; build a report from a run directory
whose episodes include the new level; continue and report an existing three-level run directory.

**Acceptance Scenarios**:

1. **Given** a signal or workshop run planned with `--level all`, **When** the dry run is printed,
   **Then** the matrix and the upper bounds include the new level after the existing three.
2. **Given** a run directory saved before this feature, **When** it is continued or reported,
   **Then** it plans exactly the episodes it planned before and reports the same tables.
3. **Given** a run whose episodes include T4 or W4, **When** it is reported, **Then** the new
   level has its own rows and comparison section, like every other level.

### Edge Cases

- **A seed for which no T4 or W4 layout satisfies the shape**: generation fails loudly naming the
  level and seed; the shipped level sizes generate for every dev and test seed (checked while
  writing this spec: all 30 seeds generate for both levels).
- **The T4 budget**: on 256 segments the full-scan rule gives a budget of 256 steps against a
  reference of about 12–13; the budget rule is not changed for one level, so T4 tells
  architectures apart by wasted probes, steps and tokens rather than by running out of budget.
- **Reading a 256-segment layout**: the start view lists the runs, as on T3; there are more of
  them, and the viewer and the text and SVG drawings must keep the pipe readable at that size.
- **A deeper recipe tree in the viewer**: 12 craftables, the three tempting items' extra inputs
  and the stock must fit the workshop drawing without overlapping labels.
- **Token and step cost**: W4's reference is about 36–41 steps, so its budget is about 108–123
  steps; dry runs show the larger upper bounds before anything is spent.
- **Levels named on the command line**: `apl signal show` and `apl workshop show` accept the new
  level and still reject unknown ones with the list of valid levels.
- **Runs that name levels explicitly**: a run planned with `--level T1,T2,T3` (or the workshop
  equivalent) plans exactly those levels, as before.

## Requirements *(mandatory)*

### Functional Requirements

**Signal trace, level T4**

- **FR-001**: The signal trace MUST offer a level T4 with 256 segments laid out as a tree with 8
  pipe ends, in which every run has at least 4 segments and no segment feeds more than two others.
- **FR-002**: T4 pipes MUST follow every rule the signal trace already has: generated from the
  level and seed only, the same seed giving the same pipe, exactly one broken segment, the layout
  given free at the start, every probe answer true.
- **FR-003**: T4's reference and budget MUST be computed by the existing rules: the worst case of
  code's probe strategy plus the submission, marked as a reference rather than an optimum, and a
  budget of the larger of 3× the reference and a full probe-by-probe scan.

**Workshop, level W4**

- **FR-004**: The workshop MUST offer a level W4 with 12 craftable items under the goal, 5 levels
  of craftables counting the goal, and 3 conflicts (3 scarce raw materials with a stock of 1, each
  with a tempting item whose first-listed recipe uses it up).
- **FR-005**: W4 workshops MUST follow every rule the workshop already has: generated from the
  level and seed only, the same seed giving the same workshop, always solvable, recipes seen only
  through `inspect`, the episode ending as stuck once the goal can no longer be made.
- **FR-006**: On every W4 workshop, a plan that always takes each item's first-listed recipe MUST
  get stuck, and the reference plan MUST craft the goal; the reference and the 3× budget MUST be
  computed by the existing rules.

**Both levels**

- **FR-007**: T4 and W4 MUST generate for every dev seed (1000–1009) and every test seed
  (2000–2019).
- **FR-008**: Adding the new levels MUST NOT change any existing level: for every seed, T1–T3 and
  W1–W3 MUST generate the same pipes and workshops, with the same references and budgets, as
  before this feature.
- **FR-009**: `--level all` for the signal trace and the workshop MUST include the new level after
  the existing ones; the new level MUST also be selectable on its own.
- **FR-010**: Runs saved before this feature MUST continue and report exactly as before; a run
  directory's planned episodes MUST NOT grow because `all` now means four levels.
- **FR-011**: `apl signal show` and `apl workshop show` MUST accept T4 and W4 respectively,
  including the reference route or plan.
- **FR-012**: The viewer MUST list the new levels for their problems and MUST draw, run live and
  replay them like the existing levels, with the pipe and the recipe tree readable at the new
  sizes.
- **FR-013**: Reports MUST show the new levels with their own rows and comparison sections, using
  each board's existing columns.

**Unchanged**

- **FR-014**: No tool, tool description, result type, prompt or architecture MUST change; every
  architecture that plays the signal trace or the workshop plays the new level without changes.
- **FR-015**: The dungeon, the survey field, the rune floor and the warehouse MUST be unchanged.
- **FR-016**: The constitution's problem rules, which name the signal levels T1–T3 and the
  workshop levels W1–W3, MUST be amended to name T1–T4 and W1–W4, with the version and the
  amendment date updated by its own versioning rule.
- **FR-017**: `plan.md` (the level tables in §2c and §2e and the milestone table) and `README.md`
  MUST describe the new levels where they describe the existing ones. (`AGENTS.md` names no level
  list, only example commands, and needs no change.)

### Key Entities

- **Signal level T4**: a level of the signal trace: segment count (256), pipe ends (8), shortest
  run (4); its pipes, references and budgets come from the existing signal rules.
- **Workshop level W4**: a level of the workshop: craftable count (12), depth (5), conflicts (3);
  its workshops, reference plans and budgets come from the existing workshop rules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For all 30 dev and test seeds, T4 and W4 generate deterministically with the shape
  FR-001 and FR-004 name.
- **SC-002**: For all 30 seeds, code's probe strategy finds the broken T4 segment within the
  reference steps for every possible broken segment, and W4's reference plan crafts the goal in
  exactly the reference steps while the first-recipe plan gets stuck.
- **SC-003**: For all 30 seeds, T1–T3 and W1–W3 are identical to their pre-feature output
  (checked against fingerprints taken before the change).
- **SC-004**: A signal and a workshop dry run with `--level all` each list 4 levels; a pre-feature
  run directory continues with exactly its original episodes.
- **SC-005**: T4 seed 1000 and W4 seed 1000 can each be shown, played live by a scripted model and
  replayed in the viewer, and drawn by their `show` commands.
- **SC-006**: The four checks (tests, lint, formatting, type check) pass, with no paid model call
  made by any test.

## Assumptions

- **T4 adds more suspects; noisy probes stay out.** The signal board is built so that "a model can
  only waste probes, never be misled". Noisy probes would change that property, so they remain for
  a later feature, as `plan.md` already says.
- **W4 grows the existing generator's knobs (craftables, depth, conflicts).** A stock of more than
  one scarce unit, or a scarce material needed in three places, would be a new kind of conflict;
  it is left out.
- **The sizes were checked before writing this spec.** With the existing generators, 256 segments
  and 8 ends generate for all 30 seeds (reference 11–12 probes, about 1.5 s for all seeds);
  128 segments with 8 ends and 256 with 12 ends did not. 12 craftables, depth 5 and 3 conflicts
  generate for all 30 seeds (reference 36–41 steps).
- **Whether the new levels actually separate the architectures** can only be measured with model
  runs. No episode is run in this feature; the comparison on the new levels belongs to M14 and
  needs the experimenter's explicit request and `--execute`.
- **Architecture code is the experimenter's.** Problems the 2026-11-03 run showed in the
  architectures (blackboard ending while a robot still carries a package; rounds replanning at a
  high cost on the warehouse) are out of scope here.
- **The combination vault** stays unbuilt, as decided after M12.
