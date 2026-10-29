# Research: Dungeon Generator, Environment, Tools and Solver

All Technical Context items were resolved from the spec, the constitution and plan.md. Nothing
is left as NEEDS CLARIFICATION.

## R1. Reproducible randomness

- **Decision**: One `random.Random` instance per dungeon, seeded with the string
  `f"apl:{level}:{seed}"`. Python stays pinned to 3.12 (`requires-python = ">=3.12,<3.13"`).
  Golden tests pin a fingerprint (SHA-256 of the canonical JSON) for a few seeds per level.
- **Rationale**: String seeding is deterministic across machines. CPython documents that only
  `random()` is guaranteed to be stable across versions; `shuffle` and `sample` could change.
  The version pin plus the golden fingerprints turn any such change into a failing test, not a
  silent change in the dungeons. Putting the level in the seed string keeps the same seed number
  independent between levels.
- **Alternatives considered**: A hand-written PRNG (more code, no gain while the Python version
  is pinned); NumPy's `Generator` (adds a dependency, which the spec doesn't need).

## R2. Generating a dungeon that meets the level rules

- **Decision**: Build each dungeon in stages and retry until it passes, using the same seeded
  RNG stream. Give up after 1,000 attempts with an error.
  1. Spanning tree with randomized Kruskal: shuffle all neighbor pairs and union-find them.
  2. Start and exit: pick randomly among the room pairs whose tree distance is at least
     2·(N−1). Such a pair always exists, because opposite corners qualify.
  3. Locked doors: pick 0, 1 or 2 doors on the tree path from start to exit, in path order
     (door A nearer the start). Removing them splits the rooms into regions R0 (start side), R1,
     and so on.
  4. Extra doors: add the level's count, choosing only between neighboring rooms *within the
     same region*. Loops therefore never bypass a lock (FR-005 holds by construction).
  5. Keys: the key for door A goes in R0, the key for door B in R1 (FR-007). Neither may be the
     start room, nor on the shortest lock-ignoring route from the start to its door (FR-006).
  6. Check: distance between start and exit ≥ 2·(N−1) *after* the extra doors are added; on
     L3, at least 2 dead ends that hold nothing (FR-008); the solver finds a solution (FR-013).
     If any check fails, retry.
  7. Labels: `rng.sample(LABEL_POOL, N*N)`, assigned to rooms in grid order (FR-017).
- **Rationale**: Constructing the structure directly (cut doors on the path, loops only inside
  regions) satisfies most rules by design, so few retries are needed. The final checks are the
  same functions the tests use, so the generator cannot hand out a dungeon the tests would
  reject. Kruskal gives a branchy tree with natural dead ends; a randomized DFS would give long
  corridors with few dead ends.
- **Alternatives considered**: Generate freely and reject until the rules hold (simple but
  needs many retries on L3); a randomized DFS tree (too few dead ends).

## R3. Room labels

- **Decision**: A fixed pool of 184 two-character labels: one letter from
  `abcdefghjkmnpqrstuvwxyz` (23 letters; no `i`, `l`, `o`) followed by one digit from `2–9`, for
  example `k3`. Each dungeon draws N² labels without repeats via `rng.sample` (step 7 in R2).
- **Rationale**: That's at least 100 labels as FR-017 requires, short enough for the text map,
  and free of easily confused characters. The labels are drawn from the seed only and are
  assigned to rooms by plain grid order. Since the draw is random, the order carries no
  information. SC-009's check (every position gets ≥ 10 labels across 100 seeds) holds easily
  with 184 labels.
- **Alternatives considered**: Word labels such as `amber-hall` (nicer, but too wide for the
  map); UUID fragments (hard to read for humans).

## R4. Solver

- **Decision**: Breadth-first search over (room, keys taken, doors opened), with sets stored as
  bitmasks. Successor order is fixed: `take` first, then `use` in direction order
  `north, east, south, west`, then `move` in the same order. Returns `Solution(actions, length)`
  or `None`. The solver works on a `Layout` (a dungeon without level, seed or solution), so
  hand-built reference dungeons can be solved too (FR-011).
- **Rationale**: Every action costs 1, so BFS is optimal. The state space is tiny: at most 25
  rooms × 4 key sets × 4 door sets. The fixed order makes the returned solution reproducible.
- **Alternatives considered**: A* (unnecessary at this size); Dijkstra (equivalent to BFS for
  unit costs).

## R5. Agent-facing boundary (Constitution II)

- **Decision**: Agent-facing code lives in two modules: `apl.dungeon.tools` (an `AgentTools`
  object with exactly `look`, `move`, `take`, `use`) and `apl.dungeon.results` (the result
  types). Architectures in `src/apl/arch/` may import only these two modules from
  `apl.dungeon`. A test reads every file under `src/apl/arch/` with `ast` and fails on any other
  `apl.dungeon` import. A second test checks that no tool result mentions a room other than the
  current one (SC-007).
- **Rationale**: Python can't truly hide object internals, so the rule is enforced where
  violations would appear: in imports and in result contents. The import test passes trivially
  today, while `src/apl/arch/` doesn't exist yet, and starts guarding in M2.
- **Alternatives considered**: Running agents in a separate process with a serialized tool
  interface (strong isolation, but far too heavy for M1).

## R6. Structured results

- **Decision**: Frozen `dataclass(slots=True)` types with a `to_dict()` that produces plain
  JSON-compatible dicts with stable key order. Error codes and end reasons are `StrEnum`s. Shapes
  are defined in [contracts/tools.md](contracts/tools.md) and
  [contracts/outcome.md](contracts/outcome.md).
- **Rationale**: Standard library only, checked strictly by mypy, and straightforward to turn
  into the JSONL rows of M2 and into the messages of a LangGraph tool node.
- **Alternatives considered**: Pydantic (adds a dependency, and nothing in M1 needs validation
  of untrusted input); TypedDicts (no immutability).

## R7. Routes and frames: one source for text map, picture and animation

- **Decision**: A route is a list of actions. `build_frames(dungeon, actions)` **replays** the
  actions through a fresh `Episode` and records one `Frame` after each step: position, inventory,
  keys still lying in rooms, opened doors, the action, its result, and whether the episode ended.
  Frame 0 is the start state. For an episode log, the recorded results are compared with the
  replayed ones, and any difference is an error. The text map, the picture and the animation are
  all drawn from these frames (FR-027).
- **Rationale**: Because the frames come from the real environment, SC-012 (the animation's
  state equals the environment's) holds by construction, and is testable in Python by comparing
  frames with episode state. The environment is deterministic, so replaying a log reproduces it
  exactly.
- **Alternatives considered**: Storing a state snapshot in every log entry (bigger logs, and
  two sources of truth); having the browser compute state incrementally (jumping and playing
  could then disagree).

## R8. Text map format

- **Decision**: An ASCII grid where each room is a fixed-width cell holding its label and
  markers. Gaps in the walls are doors, and an uppercase color letter in the wall is a locked
  door. With a route, visited rooms get a `*` marker, and a step table is printed below the map
  (step, room, action, result, marked events). The exact layout is given in
  [contracts/cli.md](contracts/cli.md).
- **Rationale**: Visit numbers for revisited rooms don't fit in a cell, so a table holds them.
  Plain ASCII works in any terminal and in test assertions.
- **Alternatives considered**: Unicode box drawing (nicer, but harder to compare in tests and
  sometimes rendered badly in Windows terminals).

## R9. Picture and animation

- **Decision**: A single HTML file. The dungeon is drawn as inline SVG, generated in Python. The
  frames are embedded as JSON in `<script type="application/json">`, and a small, hand-written
  inline script plays them. The script draws frame *i* only from `frames[i]`, never from the
  previous frame, so jumping to a step and playing to it can't disagree (FR-028).
  - **Controls**: play/pause, step back, step forward, a slider to jump, and a speed select
    (0.5×, 1×, 2×, 4×; default 1×, which is 2 steps per second). Space and the arrow keys work
    too.
  - **Motion**: transitions are turned off under `prefers-reduced-motion`.
  - **No route**: no script and no controls, just the SVG.
  - **Determinism**: `json.dumps(sort_keys=True)`, integer coordinates only, no timestamps.
  - **Safety**: the JSON escapes `</` so it can't close the script tag; text goes through
    `html.escape`.
  - **Packaging**: the player template ships as package data (`apl/dungeon/assets/player.html`)
    and is read with `importlib.resources`.
- **Rationale**: Needs no dependency and no network, and is easy to test as a string: there
  must be no `http`, `src=` or `href=` pointing outside the file. Embedding the frames as data
  keeps all game logic in Python.
- **Alternatives considered**: An animated GIF via Pillow (adds a dependency, and has no
  controls); a JavaScript library such as D3 (needs network access or a vendored copy);
  rendering with matplotlib (heavy dependency).

## R10. Command line

- **Decision**: A minimal `apl` entry point using `argparse`:
  `apl dungeon show --level L3 --seed 1000 [--route solution|FILE] [--html OUT.html]`.
  It prints the text map, and writes the picture or animation when `--html` is given. The route
  file format is in [contracts/cli.md](contracts/cli.md).
- **Rationale**: FR-024 to FR-028 are for the experimenter, so they need a way to run them.
  `argparse` is in the standard library. M2 adds `apl run` and `apl report` to the same entry
  point.
- **Alternatives considered**: Typer or Click (dependencies); helpers you can only call from
  Python (awkward for quick inspection).

## R11. Seed sets

- **Decision**: Dev seeds `1000–1009` and test seeds `2000–2019`, the same numbers for every
  level, defined as constants in `apl.dungeon.seeds`. A test asserts that the sets are disjoint.
- **Rationale**: Readable, and clearly separate. Because the level is part of the RNG seed (R1),
  the same number gives unrelated dungeons on different levels.
- **Alternatives considered**: Random seed lists (harder to read and to remember).

## R12. Scope left for M2

- Efficiency (`steps` relative to `optimal_steps`), token counts, latency and the JSONL rows
  belong to M2's runner. The M1 outcome record has the raw numbers they are built from.
- Tool descriptions written for the model belong to M2.
