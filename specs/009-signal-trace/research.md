# Research: The Signal Trace

Decisions for specs/009, in the order the plan needs them. Each says what was chosen, why, and
what else was considered. "M5" refers to specs/005-survey-field, whose shape this feature follows.

## R1. Package and problem name

**Decision**: the problem is named `signal` (CLI, run records, results). Its code lives in a new
package `src/apl/signal_trace/` with the survey package's modules: `model`, `generator`,
`strategy` (the reference, like the survey's `walk`), `env`, `tools`, `results`, `prompt`, `kit`,
`frames`, `render_text`, `render_svg`, `seeds`, `__init__`.

**Rationale**: the same layout as `apl.survey` keeps the runner's problem table, the import test
and the viewer uniform. The package is not called `apl.signal` because `signal` is a standard
library module: a module named `signal` anywhere on a path (a test folder, a script run from the
package) would shadow it.

**Alternatives**: `apl.signal` (shadowing risk, see above); `apl.pipe` (loses the board's name).

## R2. The layout is free at the start

**Decision**: the kit's `start` (the free first message every architecture gets) is the layout,
as a `look` result. `look()` returns the same layout again and costs one step. The reference
therefore needs no look: it is the strategy's worst-case probes plus one submission. The spec's
FR-005, FR-008 and FR-009 and the constitution's 2.2.0 text were updated to say so before this
plan was finished.

**Rationale**: the dungeon and the survey field both hand their start view over free through
`Kit.start` (`AgentTools.start`); making the signal trace charge a step for the same thing would
be a difference between problems with no purpose. A model that has lost the layout from its
context can still ask for it.

**Alternatives**: layout only through a paid `look` (an extra fixed step for everyone, and A1
would have nothing to read at the start); layout in the base prompt (the prompt is fixed per
problem and fingerprinted, the layout varies per seed).

## R3. Segments, runs and numbering

**Decision**: segments are numbered 1..N in depth-first preorder from S: every segment's feeder
has a lower number, and every straight piece of pipe (a *run*, ending at a junction or a pipe end)
is a contiguous range. The layout is given as runs, each `{"from": "S" | <segment>, "first": a,
"last": b}`, meaning `from` feeds `a`, `a` feeds `a+1`, …, up to `b`. A straight pipe is one run
`{"from": "S", "first": 1, "last": N}`.

**Rationale**: runs are exact, short (one line for T1 and T2, about seven for T3) and easy for a
model to read; a list of 64 `fed_from` pairs is ten times longer and hides the shape. Preorder
numbering is what makes runs contiguous.

**Alternatives**: a `fed_from` map per segment (long); random numbering (would make the board
about decoding names, not choosing probes).

## R4. Levels and the T3 tree

**Decision**:

| Level | Segments | Layout | Reference (probes + submit) | Budget |
| --- | --- | --- | --- | --- |
| T1 | 16 | one run | 4 + 1 = 5, optimal | max(15, 16) = 16 |
| T2 | 64 | one run | 6 + 1 = 7, optimal | max(21, 64) = 64 |
| T3 | 64 | a tree: each segment feeds at most two, exactly 4 pipe ends, every run at least 4 segments | about 7–8, a reference | max(≤ 27, 64) = 64 |

The T3 generator grows the tree segment by segment (each new segment extends a pipe end, or, at
three seeded moments, starts a branch from a segment that feeds only one), renumbers it in
preorder, and draws again (up to `MAX_TRIES`) when a run is shorter than 4.

**Rationale**: limiting the branching keeps a wet answer informative (it clears the whole path to
the probed segment) and the reference short. A simulation over 30 seeds per shape (2026-11-02,
greedy split strategy of R5) gave worst-case probes 6–7 for 4 ends, 7–8 for 5–6 ends, and 6 for a
line of 64. On the same 4-end trees, probing "halfway along the numbers" needs 7.7–10 probes on
average and 12–16 in the worst case, and a probe-by-probe scan 32.5 on average: the layout matters,
which is what T3 is for. With the shortest-run rule added, the naive grower is accepted about once
in 25 draws (30 of 738), so `MAX_TRIES = 1000` never runs out in practice, and the worst case is 7
probes on all 30 accepted trees; the implementation may grow branches more evenly to raise the
acceptance rate, as long as the tests' bounds hold. A test pins the bound: the reference is at most 8 probes on every T3 dev
and test seed.

**Alternatives**: unbounded random trees (a star needs up to 63 probes, so the reference and
budget blow up and the board stops showing the choice of probe); noisy probes (left for later by
the experimenter, spec Clarifications).

## R5. The reference strategy

**Decision**: one strategy for every level: probe the segment that minimises the larger of the two
possible suspect sets (ties: the lowest number), until one suspect remains, then submit it. The
reference probes are its worst case over every possible broken segment of that layout. On a single
run this is bisection, whose worst case ⌈log₂ N⌉ is optimal, so `reference_is_optimal` is true on
T1 and T2 and false on T3.

**Rationale**: the greedy split is simple, deterministic and close to optimal on the bounded trees;
an exact optimal decision tree over subsets is exponential and buys nothing for the comparison.
Using the worst case, not this seed's count, gives one reference per layout and keeps it free of
the break's position.

**Alternatives**: the probes needed for this seed's break (varies with luck, and on a line it is
sometimes fewer than log₂ N); an optimal search (cost, no benefit).

## R6. Probe semantics and suspects

**Decision**: `probe(k)` answers `water: true` exactly when no segment on the path from S to k,
k included, is broken. With one broken segment b: dry exactly when b is k or a feeder of k
upstream. The suspect set starts as every segment; a wet answer at k removes k's path from S; a dry
answer keeps only the suspects on that path. One code function computes this from a layout and a
list of answers; the environment uses it (wasted probes, frames) and A6 has its own copy built from
the layout it was given (Constitution II: architectures cannot import runner code).

**Rationale**: the physics the spec describes; it makes every answer true and deterministic.

## R7. Wasted probes

**Decision**: a successful probe is wasted when, at the time it is made, every suspect of the
current attempt gives the same answer for it: its answer was already implied. Repeats are a special
case. The episode counts `probes` (successful probe calls, every attempt) and `wasted_probes`.
Failed calls (no such segment) are invalid actions, not probes.

**Rationale**: the vault mock-up's "already ruled out" idea, made exact and computable from the
saved answers alone (SC-006).

## R8. Tool arguments and errors

**Decision**: `probe(segment)` and `submit(segment)` take a JSON integer or a string of digits (as
the survey's `submit(total)`, M5 R7). Anything else, `0`, a number above N, or `"S"`, fails with
`no_such_segment`, costs a step and is an invalid action. Other codes: `unknown_tool`,
`episode_over`. A probe result is `{"segment": k, "water": true|false}`; a submission
`{"submitted": k}`, and for a retrying architecture's wrong submission with attempts left
`{"submitted": k, "correct": false, "attempts_left": n}`, as on the survey field (specs/007 R3).

## R9. Episode, attempts and scouts

**Decision**: one agent only: `Kit.add_scout` returns None on the signal trace (no architecture
that plays it uses scouts). `MAX_ATTEMPTS = 3` for a retrying architecture; a restart costs no step,
clears the attempt's answers and keeps the pipe and its break. The episode ends at the first
submission (for A4, at a right one or one with no attempt left), at the budget, or when the
architecture stops. No `turn_source`: parallel turns are not reported on this problem.

## R10. Results and report

**Decision**: new nullable row fields `submitted_segment`, `broken_segment`, `segments`, `probes`,
`wasted_probes`; `reference_is_optimal` is shared with the survey field. They are filled from the
outcome the same way the survey's are (an attribute check), so dungeon and survey rows do not
change. The report's signal table: Right, Probes, Wasted, Efficiency, Budget hit, Tokens,
Latency (medians), and a spread table Right and Probes (min–max) with repeats. The comparison
section uses the dungeon's columns; on the signal trace A6's reference is A2 (`mapstate`), since
A2r does not play it (a per-problem override of `REFERENCES`).

**Rationale**: efficiency (reference steps ÷ steps) already carries the probes gap into the
comparison; a separate Δ probes column would say the same thing twice.

## R11. Architectures on the signal trace

**Decision**:

- A1 `react`: unchanged; the layout is its first message.
- A2 `mapstate`, A3 `plan_execute`, A4 `reflexion`: a `ProbeLog` (new `src/apl/arch/probe_log.py`,
  the signal trace's counterpart of `FieldMap`) built only from tool results: the runs, and the
  answers in the order given. It renders the layout and the answers; it draws no conclusion from
  them (no suspects), as A2's map draws none on the other problems. Its `known` count (segments
  probed) feeds A4's staleness check where rooms or cells do elsewhere. A4's restart node skips
  `kit.restart()` after a wrong segment as it does after a wrong total, because the environment
  has already restarted (contracts/architectures.md). Each module picks it with
  `kit.problem == "signal"`, next to the existing survey branch, with instructions that explain the
  log and nothing about strategy.
- A6 `hybrid`: a signal branch. Code keeps the suspect set from the answers (its own copy of R6)
  and lists options: the 8 informative probes with the smallest worst-case suspects left, best
  first, each with what it would leave (`probe 32: leaves 32 if wet, 32 if dry`), and `submit k`
  for each suspect once at most 4 remain (only `submit k` when one remains). The model answers with
  an option number, as on the dungeon; code makes the call.
- A2r, A5, A7–A9: not registered for `signal`.

**Rationale**: matches the spec (FR-021–FR-024) and the survey precedent: the memory variants
share one log so their comparison isolates the graph. Listing only 8 probes keeps A6's prompt short
on T2 without hiding the best ones; offering submissions only near the end stops a guess from being
one of 128 lines.

**Alternatives**: A6 code chooses the probe itself (no model choice left, so not a hybrid); showing
suspects to A2 (would make A2 a hybrid).

## R12. CLI

**Decision**: `apl signal show --level T2 --seed 1000 [--route reference] [--html OUT]` prints the
pipe as runs, the broken segment, the reference and the budget; `--route reference` adds the
reference strategy's probes for this break; `--html` writes the SVG page, as `apl survey show`. `apl
run --problem` takes its choices from the problem table, so `signal` is accepted there and in `apl
continue` and `apl report` through the run record.

## R13. Viewer

**Decision**: `GET /api/signal?level=&seed=` returns the pipe (segments, runs, broken, budget,
reference, `reference_is_optimal`, SVG, reference frames). The SVG follows the problem mock-up: each
run snakes 8 segments a row with a grey pipe line through the centres, runs are stacked, and each
starts at an inlet labelled "S" or "from 18" (a line from a far feeder would cross the board). Boxes
carry `data-seg`, and the page draws on it: the water line along the segments known to be wet, a dot
for a wet probe and a cross for a dry one, shaded suspects, the last suspect in red, the broken
segment's ring hidden under "Agent's view", and probes, suspects left, wasted probes and the
submission in the stats panel. The "Shortest solution" toggle becomes "Reference probes" and numbers
the reference's probes. Episode start, step, restart and end events keep their shape; the start
event adds `problem`, `segments` and `broken`.

**Rationale**: the dungeon drawing (positions, trails, doors) has nothing to move here, so the page
needs its own small branch; the events and the replay mechanism stay as they are.

## R14. Fairness checks

**Decision**: the import test's allowed list gains `apl.signal_trace.tools` and
`apl.signal_trace.results`, and a test like M5's shows the generator, environment and strategy are
forbidden. A boundary test plays random calls and checks every result's shape, and that the
results do not depend on the break beyond what the probe answers say: the start and `look` results
are identical for the same layout with any broken segment, and every probe answer equals R6's rule.
(A text search for the broken number cannot work here: every segment number is in the layout.) AGENTS.md's list of
allowed imports and tools is updated to match.
