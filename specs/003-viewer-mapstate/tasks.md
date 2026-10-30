---

description: "Task list for M3: browser viewer and A2 map state"
---

# Tasks: Browser Viewer and A2 Map State

**Input**: Design documents from `specs/003-viewer-mapstate/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R17), data-model.md, contracts/
(viewer-api.md, mapstate.md, cli.md), quickstart.md

**Tests**: Requested. The spec's success criteria (SC-001 to SC-009) are test outcomes, so every
phase starts with its tests. Write them first, see them fail, then implement. The page's
JavaScript is checked by hand (quickstart), plus a test that the elements it uses exist.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on
its own.

**Rules for every task**:

- **Types and data**: full type hints (mypy strict). Frozen `@dataclass(slots=True)` unless
  data-model.md says mutable (`DungeonMap`, `EpisodeSession`).
- **No network in tests**: no test makes a network call or a model call (Constitution VI). Tests
  use `ScriptedChatModel` and `scripted_factory` from `tests/runner/scripted.py`.
  `tests/conftest.py` blocks sockets; only the one loopback test in T020 lifts that, and only for
  `127.0.0.1`.
- **Imports**: `apl dungeon show` must not import LangChain. `apl serve` imports the runner and
  LangChain lazily inside its code path, as `apl run` does.
- **Who writes A2**: the experimenter asked the agent to write A2 (spec Assumptions), so T034
  and T035 are agent tasks. A1 (`src/apl/arch/react.py`) is not changed.
- **Shared setup**: the base prompt, the tool schemas and `prompt_fingerprint()` stay unchanged.
- **Untrusted text in the page**: all model and tool text in `index.html` is inserted with
  `textContent`, never `innerHTML`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1–US4)

## Path Conventions

Single project: `src/apl/` and `tests/` at the repository root, as in plan.md.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: package skeletons, so later tasks have files to fill.

- [X] T001 Create `src/apl/viewer/__init__.py` (a one-line docstring), `src/apl/viewer/assets/`
  (shipped like `src/apl/dungeon/assets/player.html`) and `tests/viewer/__init__.py`. Confirm with
  `importlib.resources.files("apl.viewer") / "assets"` in a throwaway check that uv_build
  includes the folder.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**:

- the vLLM provider and its settings (research R9);
- context overflow as the architecture's failure (R10);
- the observation hooks (R3);
- the scripted replay fix that A2 needs (R17).

Every story depends on this phase.

### Tests for Phase 2 ⚠️ (write first, they must fail)

- [X] T002 [P] Extend `tests/runner/test_settings.py`:
  - the default `model` is `vllm:qwen3.5-9b`;
  - `APL_BASE_URL` is read, with default `http://localhost:8001/v1`;
  - `max_output_tokens` resolves to 1,024 for `vllm:` and 4,096 for other providers when
    `APL_MAX_OUTPUT_TOKENS` is unset, and to the variable when it is set;
  - `record()` has `base_url` for `vllm:` and `null` otherwise, and takes the server's `num_ctx`
    for `vllm:`;
  - `required_key_var("vllm:x")` is `None`.

  Per contracts/cli.md "Settings".
- [X] T003 [P] Create `tests/runner/test_vllm.py`:
  - **Reasoning capture**: `VLLMChat` copies `message.reasoning` (and the older
    `reasoning_content`) from a chat-completions response into
    `additional_kwargs["reasoning_content"]`. Build the response with the `openai` types; no
    network.
  - **Not sent back**: `langchain_openai.chat_models.base._convert_message_to_dict` on an
    `AIMessage` carrying `reasoning_content` produces no reasoning field.
  - **Context lookup**: `server_context(base_url, transport=httpx.MockTransport(...))` returns
    `max_model_len` from `GET /models`, and returns `None` when the server cannot be reached.

  Per research R9.
- [X] T004 [P] Create `tests/runner/test_episode_hooks.py`:
  - `Episode.on_step` is called once per logged call, uncounted `episode_over` calls included,
    with the `LogEntry`;
  - `frames.snapshot` equals the frames `build_frames` makes;
  - `play_episode(..., callbacks=[h], on_episode=f)` calls `f` with the episode before the first
    model call, and `h` sees every model call next to the meter;
  - a scripted model raising a fake error with `status_code=400` and "maximum context length" in
    its message ends the episode `stopped`, with `arch_error` starting
    "context window exceeded". It is scored, and the run does not stop;
  - the same for an error whose `code` is `context_length_exceeded`;
  - any other 400 still raises `PermanentProviderError`.

  Per research R3 and R10.
- [X] T005 [P] Update `tests/runner/test_cli_run.py`: the dry run names the new default model
  `vllm:qwen3.5-9b` and shows `context  from the server (read at --execute)` for `vllm:` models.
  Keep the Ollama context line test with `APL_MODEL=ollama:qwen3:8b`. Per contracts/cli.md
  "apl run".

### Implementation for Phase 2

- [X] T006 Update `src/apl/runner/settings.py`:
  - default `model = "vllm:qwen3.5-9b"`;
  - `base_url` from `APL_BASE_URL`;
  - `max_output_tokens: int | None`, resolved per provider (`resolved_max_output_tokens()`);
  - `num_ctx` recorded for `vllm:` too (the server's value, set through `with_server_context` in T007/T008);
  - `base_url` in the record.

  Then fix the callers in `src/apl/runner/run.py` and `src/apl/runner/spec.py`. Makes T002 pass.
- [X] T007 Create `src/apl/runner/vllm.py`:
  - `VLLMChat(ChatOpenAI)`, overriding `_create_chat_result` to copy the reasoning into
    `additional_kwargs["reasoning_content"]` on each generation;
  - `server_context(base_url, transport=None) -> int | None`, using `httpx` with a 5 s timeout.

  Makes T003 pass.
- [X] T008 Update `src/apl/runner/run.py`:
  - `default_model_factory` builds `VLLMChat(model=<name>, base_url=settings.base_url,
    api_key="EMPTY", max_tokens=..., timeout=..., max_retries=..., temperature=...)` for
    `vllm:`, adding callbacks as the other providers do;
  - `execute()` records `server_context()` as `num_ctx` for `vllm:`.

  Update `src/apl/runner/spec.py` `format_plan` to print the vLLM context line. Makes T005 pass.
- [X] T009 [P] In `src/apl/dungeon/env.py`, add `on_step: Callable[[LogEntry], None] | None`,
  initialised to `None` in `__init__`, and call it at the end of `_call()` for both the counted
  and the `episode_over` branch. In `src/apl/dungeon/frames.py`, rename `_snapshot` to `snapshot`
  and update its two callers.
- [X] T010 Update `src/apl/runner/episode.py`:
  - `play_episode(..., callbacks: Sequence[BaseCallbackHandler] = (), on_episode=None)`:
    callbacks go to `model_factory(settings, [meter, *callbacks])`, and `on_episode(episode)` is
    called before `build_kit`;
  - an `_is_context_overflow(error)` check (status 400 with "maximum context length" in the
    message, or `code == "context_length_exceeded"`), tested before the permanent-status
    branch. It records `arch_error = "context window exceeded: " + _describe(error)`.

  Makes T004 pass.
- [X] T011 [P] In `tests/runner/scripted.py`, make `replay_solution` count its own calls (a
  closure counter, `per_turn` actions per call) instead of counting `ToolMessage`s in its input.
  The A1 tests in `tests/arch/test_react.py` and the replays in `tests/runner/test_run.py` must
  still pass. Per research R17.

**Checkpoint**: `uv run pytest` passes. `uv run apl run --arch react --level L1 --seeds dev
--limit 1` prints a vLLM plan.

---

## Phase 3: User Story 1 - Browse dungeons by level and seed (Priority: P1) 🎯 MVP

**Goal**: `apl serve` shows any level and seed as a drawing, with budget, optimum and a
shortest-solution toggle. Test seeds are refused.

**Independent Test**: start the viewer, show L3 1000, 4242 and 1000 again (the first and last
are identical), toggle the solution, and get a refusal for 2003.

### Tests for User Story 1 ⚠️ (write first, they must fail)

- [X] T012 [P] [US1] Extend `tests/dungeon/test_render.py`: `render_html` and `_svg` contain
  exactly one `<rect class="room" id="room-x-y">` per room, and the existing wall, key and label
  checks still pass. Per research R6.
- [X] T013 [P] [US1] Create `tests/viewer/test_app.py` (dungeon part), calling `apl.viewer.app`
  functions directly:
  - `options()` lists the levels, the dev seeds, the test-seed range, the written architectures
    (sorted), the model, the settings and `can_run`;
  - `dungeon("L3", "1000")` has every field of contracts/viewer-api.md, and two calls give
    identical bodies (SC-001);
  - `solution` starts at the start, ends at the exit, and has `optimal_steps + 1` frames;
  - test seed 2003 gets 403 with the test-seed message;
  - `"-1"`, `"abc"` and level `L9` get 400;
  - seed 4242 works (outside both sets);
  - `can_run` is `False` for `openai:x` without `execute=True`, and `True` for `vllm:` and
    `ollama:` (research R8).
- [X] T014 [P] [US1] Create `tests/viewer/test_page.py`: the shipped `index.html` contains the
  element ids the script uses (level, seed, random, generate, arch, run, stop, saved, map, slider,
  follow, fog toggle, solution toggle, panel, stats). The script contains no `innerHTML` or
  `insertAdjacentHTML` with a variable.

### Implementation for User Story 1

- [X] T015 [US1] In `src/apl/dungeon/render_html.py` `_svg`, draw `<rect class="room"
  id="room-{x}-{y}" x=… y=… width=CELL height=CELL/>` per room, right after the floor rect. In
  `src/apl/dungeon/assets/player.html`, give `.room` no visible style, so the M1 output looks the
  same. Makes T012 pass.
- [X] T016 [US1] Create `src/apl/viewer/app.py` with `Viewer` (data-model.md "Viewer"):
  - `options()` and `dungeon(level, seed)`, returning `(status, content_type, body)`;
  - seed parsing and the test-seed check, in a helper reused by T024.

  `Viewer` takes `settings`, `execute`, `results_dir`, `model_factory` and `architectures`
  (defaults: `default_model_factory`, `registry`). Makes T013 pass.
- [X] T017 [US1] Create `src/apl/viewer/server.py`:
  - `make_server(viewer, port) -> ThreadingHTTPServer`, bound to `127.0.0.1`;
  - a `BaseHTTPRequestHandler` that routes `GET /`, `GET /api/options` and
    `GET /api/dungeon`, parses query strings with `urllib.parse`, and returns JSON errors as
    `{"error": ...}`;
  - quieter request logging (no per-request lines).
- [X] T018 [US1] Add `apl serve [--port N] [--execute]` to `src/apl/cli.py`, with lazy imports:
  - load the settings (exit 2 on error);
  - for `vllm:`, read `server_context()`, and warn if it is `None`;
  - print `Viewer: http://127.0.0.1:<port>/ (model <model>; Ctrl-C to stop)`, then
    `serve_forever()`.

  Per contracts/cli.md "apl serve".
- [X] T019 [US1] Create `src/apl/viewer/assets/index.html`, browse part:
  - a layout with a controls row (level, seed, random, dev-seed quick picks, Generate), the map
    area and a stats line (budget, optimal);
  - fetch `/api/dungeon` and insert its `svg`;
  - the shortest-solution toggle draws a dashed polyline from `solution` frames, using
    `cell`/`margin` as `player.html` does;
  - random seeds come from 0–999,999, skipping the test seeds;
  - errors are shown in a message line, and the old map stays.

  Styles follow `player.html`. Makes T014 pass for the browse elements.
- [X] T020 [P] [US1] Create `tests/viewer/test_server.py` with a fixture that restores
  `socket.socket.connect` for `127.0.0.1` only. Start `make_server(viewer, 0)` in a thread, then
  `GET /`, `/api/options` and `/api/dungeon?level=L1&seed=1000` through `http.client`, and check
  the statuses and content types. Shut down in a `finally`.

**Checkpoint**: `uv run apl serve` shows and regenerates dungeons in the browser. US1 is usable on
its own.

---

## Phase 4: User Story 2 - Watch an agent play live (Priority: P2)

**Goal**: start A1 (or any written architecture) on the shown dungeon, watch steps, model turns
and stats live, stop it, scrub, and use the agent's view. One episode at a time.

**Independent Test**: with the scripted model, start an episode through the app, read its event
stream, and check the order, contents, stop and 409.

### Tests for User Story 2 ⚠️ (write first, they must fail)

- [X] T021 [P] [US2] Create `tests/viewer/test_events.py`:
  - **Session streams**: `EpisodeSession.emit`/`stream` gives every earlier event to a late
    reader, then new ones until done (SC-003). `events.jsonl` equals `events`.
  - **Thinking events**: `ViewerCallbacks` emits `thinking` whose `new_input` is the input
    after the longest prefix shared with the previous call's input, comparing by the same key as
    `Transcript.add`. Cover three cases:
    - an A1-style growing history gives only the new tail;
    - an A2-style input gives the previous turn and the map every time;
    - an identical map in two consecutive calls appears in both.
  - **Turn events**: `turn` carries the text, the reasoning (from
    `additional_kwargs["reasoning_content"]`), tool calls, usage, latency and `output_limit_hit`.
  - **Callback errors**: an exception inside `ViewerCallbacks` does not end the episode
    (`raise_error=False`).
- [X] T022 [P] [US2] Extend `tests/viewer/test_app.py` (episodes part), with a scripted model and
  `replay_solution` on L1 1000 through `react`. `start_episode` returns 201 and an id matching
  contracts/viewer-api.md. The full event list has:
  - `start` first and `end` last;
  - each `thinking` followed by its `turn`, then that turn's `step`s in order;
  - `optimal_steps` step events;
  - an `end` row with success.

  Also check:

  - `list_episodes()` lists the running episode first with `running: true` (FR-014: the page
    finds it after a reload);
  - a second `start_episode` while one runs gets 409 with `running`. Use a strategy that blocks
    on a `threading.Event`;
  - `stop` gets 202, emits `stopping`, and the episode ends `stopped` after the current turn;
  - stopping an unknown id gets 404;
  - a test seed or `can_run=False` gets 403, and an unknown or unwritten architecture gets 400;
  - a provider error (fake 503 after retries) ends with an `end` event whose row has
    `status == "error"`, and the viewer can start another episode afterwards (FR-017).

### Implementation for User Story 2

- [X] T023 [US2] Create `src/apl/viewer/events.py`:
  - `EpisodeSession`: `emit`, `stream(from_index)` and a `done` flag, under a
    `threading.Condition`, appending each event to `events.jsonl`;
  - `ViewerCallbacks(BaseCallbackHandler)`, with `raise_error = False`, and `new_input` as the
    part after the shared prefix with the previous call's input, using keys shared with
    `apl.runner.meter.Transcript`. Add a small public `message_key(message)` helper in
    `meter.py` instead of duplicating the JSON key.

  Per data-model.md. Makes T021 pass.
- [X] T024 [US2] In `src/apl/viewer/app.py`, add `list_episodes()` (the running session only; T035 adds saved ones), `start_episode(arch, level, seed)`,
  `stop_episode(id)` and the running-session lock:
  - the worker thread calls `play_episode` with `callbacks=[ViewerCallbacks(session)]` and
    `on_episode`, which sets `episode.on_step` to emit `step` with `frames.snapshot(...)`, the
    result and the current call number;
  - it emits `start` and `end`;
  - it writes `outcome.json`, `conversation.json` and `episode.json` into
    `results/viewer/<id>/` (data-model.md "Saved episode folder"), using `write_json` from
    `apl.runner.results` and `_code_version`/`_versions` from `apl.runner.run`. Make those two
    public if needed.

  Makes T022 pass.
- [X] T025 [US2] In `src/apl/viewer/server.py`, add:
  - `GET /api/episodes`;
  - `POST /api/episodes` (a JSON body, at most 4 KiB);
  - `POST /api/episodes/<id>/stop`;
  - `GET /api/episodes/<id>/events` as SSE (`text/event-stream`, `Cache-Control: no-cache`,
    `id/event/data` lines, a flush after each event, and a comment line every 15 s while idle so
    a dropped page is noticed);
  - id matching against the contract's pattern before any lookup.
- [X] T026 [US2] In `src/apl/cli.py` `serve`, on Ctrl-C:
  - stop a running episode (`episode.stop()`);
  - wait up to `settings.timeout_s` for its thread, so it ends and is saved `stopped`;
  - close the server and exit 130.
- [X] T027 [US2] Extend `src/apl/viewer/assets/index.html`, live part:
  - **Controls**: the architecture select from `/api/options`; Run, disabled with
    `cannot_run_reason` when `can_run` is false; Stop.
  - **Event stream**: an `EventSource` on the events URL.
  - **Waiting**: a "waiting for the model (n s)" line between `thinking` and `turn`.
  - **Turn cards**: one card per turn, with collapsible new input and reasoning, the text, and
    each tool call with its result. Each step links to its map step.
  - **Map from frames**: redraw the agent, trail, failure flash, taken keys and opened doors from
    `frame` dicts, as in `player.html`'s `render(n)`.
  - **Stats**: steps/budget, optimal, calls, tokens, elapsed time, and at the end the end reason
    and efficiency.
  - **Step slider** with a "follow live" toggle, off when the user scrubs.
  - **Agent's view**: the toggle sets class `fog` on rooms not visited up to the shown step.
  - **Single episode**: a 409 shows its message.

  On page load, if `/api/episodes` lists a running episode, attach to it (FR-014). Makes T014
  pass fully.

**Checkpoint**: A1 can be watched live on vLLM. Reload, Stop and scrub work.

---

## Phase 5: User Story 3 - A2: an agent with an explicit map (Priority: P3)

**Goal**: `mapstate` is written, registered, and watchable. Its map comes only from tool
results and replaces the history.

**Independent Test**: scripted A2 episodes are checked against the oracle after every step, and
its recorded inputs have the contract's layout.

### Tests for User Story 3 ⚠️ (write first, they must fail)

- [X] T028 [P] [US3] Create `tests/arch/oracle.py`: `expected_map(dungeon, frames, upto)`
  returns the map that the tool results up to step `upto` reveal (research R17):
  - the visited rooms by label;
  - their doors and items as they are now, except that a door opened from the other side shows as
    still locked until a move through it;
  - the walked edges in both directions;
  - the inventory;
  - the opened doors with colors.

  It reads the layout (a test may; an architecture may not).
- [X] T029 [P] [US3] Create `tests/arch/test_dungeon_map.py`:
  - the apply rules of research R13, one test each;
  - the invariants in data-model.md;
  - US3/AC3: `move east` from X to Y gives X east → Y and Y west → X;
  - US3/AC4: after `take` and `use`, and then several moves, the door shows as opened with its
    color and the key is in the inventory;
  - failed results change nothing;
  - the render format of contracts/mapstate.md, with an exact expected string for a small route;
  - SC-007: scripted routes on the 5 reference layouts in `tests/dungeon/reference.py` and on dev
    dungeons of L1–L3 match `expected_map` after every step before the end. Include a failed
    move, a locked move, a revisit and several calls in one turn;
  - SC-008: fully exploring every L3 dev dungeon (by walking the layout in the test) keeps
    `render()` at most `8192 // 4` characters.
- [X] T030 [P] [US3] Create `tests/arch/test_mapstate.py`:
  - **SC-006**: `replay_solution` on every dev dungeon of L1–L3 succeeds with efficiency 1.0;
  - **US3/AC5**: a recording strategy shows that the first call's input is
    `[System(base + MAP_INSTRUCTIONS), Human(start), Human(map)]`, and each later call's input
    is `[System, AI(prev), Tool..., Human(map)]`;
  - **US3/AC6**: at step 30, on an L3 budget run (bump a wall, then wander), no reply or result
    from steps 1–28 is in the input;
  - **FR-024**: a text answer ends `stopped`; running into the budget ends `budget`;
  - **FR-024**: batches that reach the exit or the budget end cleanly;
  - `MAP_INSTRUCTIONS` contains no digits;
  - **US3/AC8**: in a viewer episode with `mapstate`, every `thinking` after the first has the
    map text in `new_input`.

### Implementation for User Story 3

- [X] T031 [US3] Create `src/apl/arch/dungeon_map.py` with `RoomNote` and `DungeonMap`
  (`from_start`, `apply`, `unexplored`, `render`), per data-model.md and contracts/mapstate.md.
  It imports nothing from `apl` except, optionally, `apl.dungeon.results`. Makes T029 pass.
- [X] T032 [US3] Create `src/apl/arch/mapstate.py`:
  - `MAP_INSTRUCTIONS` (research R15: explains the map only, no strategy, no digits);
  - `play(kit)`, with a `StateGraph` whose state keys `messages` and `map` have no reducers;
  - an `agent` node that builds the input of contracts/mapstate.md;
  - an `act` node that calls `kit.tool_node`, pairs the replies with `tool_calls` +
    `invalid_tool_calls` by `tool_call_id`, and applies each result to the map;
  - the route as in A1;
  - `recursion_limit` from the kit.

  Makes T030 pass.
- [X] T033 [US3] Register `"mapstate": "apl.arch.mapstate"` in `src/apl/runner/registry.py`.
  Check that `tests/dungeon/test_boundary.py` now scans both new files and passes, and that
  `apl run --arch react,mapstate --level L1 --seeds dev --limit 1` plans 2 episodes.

**Checkpoint**: `mapstate` appears in the viewer, and its turn cards show the map.

---

## Phase 6: User Story 4 - Replay saved episodes (Priority: P4)

**Goal**: saved episodes are listed and replay exactly as shown live. Their files work with
`apl dungeon show`.

**Independent Test**: play a scripted episode, then load it from the saved list. Its events are
identical, and its outcome file animates in `apl dungeon show`.

### Tests for User Story 4 ⚠️ (write first, they must fail)

- [X] T034 [P] [US4] Extend `tests/viewer/test_app.py` (replay part):
  - `list_episodes()` returns the saved episodes newest first, with the running one first and
    `running: true`. Each entry has the fields in contracts/viewer-api.md;
  - `EpisodeSession.load(folder)` yields exactly the events seen live (SC-004);
  - ids with `..`, `/` or a wrong pattern get 404 without touching the file system;
  - the saved `outcome.json` parses with `apl.dungeon.frames.parse_route_file` and replays
    without error (US4/AC3);
  - a stopped and an error episode are saved and listed too.

### Implementation for User Story 4

- [X] T035 [US4] In `src/apl/viewer/app.py`, extend `list_episodes()` with saved episodes (it reads `episode.json` of
  each folder under `results/viewer/` and skips unreadable ones) and saved-episode lookup for
  `events`. Add `EpisodeSession.load` in `src/apl/viewer/events.py`. In
  `src/apl/viewer/server.py`, serve saved events from the same SSE endpoint (`GET /api/episodes`
  already exists from T025). Makes T034 pass.
- [X] T036 [US4] Extend `src/apl/viewer/assets/index.html`:
  - a "saved episodes" select (refreshed after each `end`);
  - loading a saved episode loads its dungeon and replays its events through the same drawing
    code;
  - Play/Pause and speed for replays, as in `player.html`;
  - the slider works the same as live.

**Checkpoint**: all four stories work. Quickstart steps 1–6 pass.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T037 [P] Update the docs:
  - `README.md`: a "Watch an agent" section (`uv run apl serve`, what the page shows, where
    episodes are saved); the Model section for vLLM (`vllm:qwen3.5-9b`, `APL_BASE_URL`, the
    8,192 context, Ollama still supported); the Layout section, adding `src/apl/viewer/`;
  - `AGENTS.md`: the `uv run apl serve` command;
  - `plan.md` §9: vLLM as the default model;
  - `.env.example`: `APL_MODEL=vllm:qwen3.5-9b` and `APL_BASE_URL`.
- [X] T038 [P] In `tests/viewer/test_app.py`, check that a viewer episode and an `apl run`
  episode on the same dungeon and scripted model give the same `EpisodeRow`, apart from
  `run_id` and `latency_s` (Constitution I, FR-007).
- [X] T039 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` and
  `uv run mypy`; all must pass.
- [X] T040 Run quickstart.md against the real vLLM server:
  - start `apl serve` and check `/api/options` and `/api/dungeon` with `curl`;
  - start one A1 and one A2 episode on L1 1000 through the API;
  - confirm that the events stream and the episodes are saved.

  The browser steps (3–8) are checked by the experimenter.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: depends on Setup and blocks every story. T009 and T010 are needed
  by US2; T011 is needed by US3; T006–T008 are needed by everything that loads settings.
- **US1 (P1)**: after Foundational.
- **US2 (P2)**: after US1, because it extends `app.py`, `server.py`, `cli.py` and
  `index.html`.
- **US3 (P3)**:
  - T028, T029 and T031 need only Foundational and can run beside US1/US2;
  - T030's last check (US3/AC8) and T033's viewer use need US2;
  - T032 needs T031.
- **US4 (P4)**: after US2, because saving happens in T024.
- **Polish**: after all stories.

```text
Setup → Foundational ─┬─ US1 ── US2 ─┬─ US4 ──┐
                      │              └─ US3 (T030 AC8, T033) ─┴─ Polish
                      └─ US3 map work (T028, T029, T031, T032) ┘
```

### Within Each Story

Tests first, and they must fail. Then implementation in task order. The story is done when its
tests pass and its checkpoint holds.

### Parallel Opportunities

- **Foundational:** T002–T005 together; T009 and T011 beside T006–T008.
- **US1:** T012–T014 together; T020 once T017 exists.
- **US2:** T021 and T022 together.
- **US3:** T028–T030 together; the map work (T028, T029, T031) can run beside US1 and US2.
- **US4:** T034 beside US3.
- **Polish:** T037 and T038 together.

---

## Parallel Example: Phase 2

```text
Task: "T002 Extend tests/runner/test_settings.py for vllm defaults"
Task: "T003 Create tests/runner/test_vllm.py"
Task: "T004 Create tests/runner/test_episode_hooks.py"
Task: "T005 Update tests/runner/test_cli_run.py"
```

## Parallel Example: A2 map beside the viewer

```text
Task: "T028 Create tests/arch/oracle.py"
Task: "T029 Create tests/arch/test_dungeon_map.py"
Task: "T031 Create src/apl/arch/dungeon_map.py"   # after T029 is written
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 and Phase 2: vLLM works in `apl run`, and the hooks exist.
2. Phase 3: `apl serve` shows dungeons.
3. Stop and check: the experimenter browses dungeons in the browser.

### Incremental Delivery

1. US1: browse dungeons.
2. US2: watch A1 live. This is the core of the milestone.
3. US3: A2 appears in the list.
4. US4: replay saved episodes.
5. Polish: docs and the real-server check.

---

## Notes

- `[P]` tasks touch different files and do not depend on incomplete tasks.
- The page is one file that several tasks extend (T019, T027, T036), so they run in that order.
- Commit only when the experimenter asks.
- `.env` holds the real OpenAI key and must never be committed. It now sets
  `APL_MODEL=vllm:qwen3.5-9b`.
