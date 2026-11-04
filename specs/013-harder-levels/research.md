# Research: Harder Top Levels (specs/013)

Every decision below was checked against the current code on 2026-11-03, with the two new levels
patched into `LEVELS` in a scratch process (no file changed).

## R1. T4's size

- **Decision**: `SignalLevel("T4", segments=256, ends=8, min_run=4)`.
- **Rationale**: The existing tree generator builds it for all 30 dev and test seeds, and
  `worst_case` gives 11–12 probes (reference steps 12–13). It quadruples T3's segments and doubles
  its branches (15 runs instead of 7), so choosing the probe that best splits the suspects means
  weighing far more subtrees, which is the property the board measures.
- **Alternatives**: 128 segments with 8 ends (27 of 30 seeds fail the run-length rule within
  `MAX_TRIES`); 256 segments with 12 ends (all 30 fail, 34 s); noisy probes (would break the
  board's "never misled" property; left for a later feature, as `plan.md` already says).

## R2. T4's budget

- **Decision**: Unchanged rule: `max(3 × reference_steps, segments)`, which gives 256 on T4.
- **Rationale**: The constitution states the signal budget rule for every level. A tighter T4
  budget would be a rule change for one level. With the scan rule, T4 separates architectures by
  wasted probes, steps, efficiency and tokens, the columns the signal report already has.
- **Alternatives**: 3× the reference only (about 36–39 steps): would make the budget bite but
  needs a constitution rule change and a second budget rule; rejected for this feature.

## R3. W4's size

- **Decision**: `WorkshopLevel("W4", 12, 5, 3)`: 12 craftables, depth 5, 3 conflicts.
- **Rationale**: The existing generator builds it for all 30 seeds (reference 36–41 steps,
  budget 108–123). It needs 15 craftable names (20 exist) and 7 raw names (14 exist). Every
  existing per-level property holds on all 30 seeds: shape (12 craftables, depth 5, 3 two-recipe
  items, 3 scarce with stock 1), the reference plan crafts the goal in its steps, the greedy
  first-recipe plan gets stuck, and the scripted planner fits the budget.
- **Alternatives**: a scarce stock of 2 with three uses, or one scarce material in three places:
  new kinds of conflict that the generator and the waste rule do not model; left out.

## R4. Existing levels stay byte-identical

- **Decision**: Add a pinned-output test before any change (T001-style): for every seed in dev
  and test, a hash of each T1–T3 pipe (feeder, broken, reference) and each W1–W3 workshop
  (recipes, stock, scarce, reference choice, reference), compared to a fixture written from the
  current code.
- **Rationale**: Both generators seed their RNG with `"<problem>:<level>:<seed>"`, so adding a
  level cannot change another level's draws; the pinned test proves it (SC-003).
- **Alternatives**: relying on the RNG keying alone: an argument, not a check.

## R5. The pinned dry-run plans

- **Decision**: `tests/runner/test_signal_pinned.py` and `test_workshop_pinned.py` build their
  plans with `["all"]`, which will now include the new level. Change them to name the existing
  levels explicitly (`["T1", "T2", "T3"]`, `["W1", "W2", "W3"]`); their fixture files stay byte for
  byte as they are.
- **Rationale**: Those tests pin what the earlier milestones shipped. With explicit levels they
  keep doing that, and a new test covers `all` including the new level (FR-009).
- **Alternatives**: regenerating the fixtures with `GOLDEN_REGEN=1`: would silently accept any
  change to the old levels' plan lines.

## R6. Saved runs

- **Decision**: No change to `run.json` or `apl continue`.
- **Rationale**: `run.json` stores the resolved level list (for example `["T1", "T2", "T3"]`),
  not `all`, so a saved run continues with exactly its levels (FR-010). A test continues a
  three-level signal run directory after the change and checks its plan.

## R7. Where the level lists are written out

- **Decision**: `src/apl/cli.py` builds the `apl signal show` and `apl workshop show` level
  choices from the problems' `LEVELS` (as `apl dungeon show` already does) instead of the literal
  lists. The viewer's level lists, the run planner's `all` and the report already read `LEVELS`
  through `apl.problems`, so they need no change.
- **Tests that name the level lists**: `tests/viewer/test_signal.py` and
  `tests/viewer/test_workshop.py` (the options' level lists), `tests/signal_trace/test_generator.py`
  (the budget table, a T4 shape test like T3's), `tests/workshop/test_generator.py` (`SHAPE`,
  `BOUND`: `BOUND` is 4× the craftables, so 48 for W4).
- **Alternatives**: adding `"T4"` and `"W4"` to the literal lists: the next level would need the
  same edit again.

## R8. Drawing a 256-segment pipe

- **Decision**: In `src/apl/signal_trace/render_svg.py`, a row holds 8 segments on pipes of up to
  64 segments (T1–T3, unchanged) and 24 on longer pipes (T4).
- **Rationale**: With 8 a row, T4 draws 300 × 1186–1290 px; the viewer scales the drawing to the
  map's width, so it would run to several screens. With 24 a row it is 716 × 640–744 px, about
  square; 16 gives 508 × 796–900, 32 gives 924 × 614–692. T1–T3 keep 8, so their SVG is unchanged.
  The page reads every segment's position from the drawn boxes (`centreOf`), so no page code
  depends on the row width.
- **The label column grows too.** Feeder labels are right-aligned at x = 59 in 12 px monospace
  (about 7.2 px a character). T3's longest, `from 18`, starts near x = 9; T4's three-digit
  feeders (`from 194` on seed 1000) start near x = 1, so a slightly wider font clips them. On
  pipes over 64 segments `LABEL` is 80 instead of 64 (T1–T3 keep 64). A render test checks that
  every label's estimated start (anchor − characters × 7.2) is at least `MARGIN` / 2 inside the
  viewBox, on every T4 seed.
- **Alternatives**: one row width for every level (changes T1–T3's drawings); a zoom control in
  the viewer (more code than the problem needs).

## R9. Drawing a W4 workshop

- **Decision**: No change to `src/apl/workshop/render_svg.py`.
- **Rationale**: W4's widest row has 7 boxes (W3: 6) and its raw row 7; 7 rows in all. The
  drawing grows to about 770 px wide and scales like W3's. This is checked by eye in the viewer
  (quickstart) and by a new W4 case in `tests/workshop/test_render.py` (the existing render tests
  use W3 only).

## R10. Test time

- **Decision**: Accept it; cache nothing for now.
- **Rationale**: The parametrized signal tests over `sorted(LEVELS)` add about 8 s for T4 (about
  50 ms a pipe, generated once per test for 30 seeds). W4 adds well under a second.
- **The strategy test checks only the seeded break.** `test_the_reference_finds_the_break_within_its_probes`
  plays one broken segment per seed (`pipe.broken`). SC-002 asks for every possible broken
  segment, so a new test, parametrized over `sorted(LEVELS)`, replaces `broken` with each segment
  1..N on every seed and checks that the reference strategy submits it with at most
  `reference_probes` probes, every answer true. Measured on T4 in a scratch run: 0 failures over
  30 × 256 cases in 2.8 s.

## R11. Constitution amendment

- **Decision**: Version 2.5.0 → 2.5.1 (PATCH), last amended 2026-11-03: "Levels T1–T3" →
  "Levels T1–T4" and "Levels W1–W3" → "Levels W1–W4". The Sync Impact Report notes this feature.
- **Rationale**: No rule changes. The budget, reference and solvability rules stay word for word,
  and only the named level range grows; the governance rule calls that a clarification (PATCH).
- **Alternatives**: MINOR: kept for adding or materially expanding a principle or section, which
  this does not do.
