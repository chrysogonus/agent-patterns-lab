---

description: "Task list for M2: runner, results format, report and A1 ReAct"
---

# Tasks: Runner, Results Format, Report and A1 ReAct

**Input**: Design documents from `specs/002-runner-react/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (kit.md, cli.md,
results.md), quickstart.md

**Tests**: Requested. The spec's success criteria (SC-001 to SC-010) are test outcomes, so every
story phase starts with its tests. Write them first, see them fail, then implement.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on
its own.

**Rules for every task**:
- Full type hints (mypy strict). Frozen `@dataclass(slots=True)` unless data-model.md says mutable.
- No test makes a network call or a paid call (Constitution VI). `tests/conftest.py` (T004) blocks
  the network; tests use the scripted model (T011).
- `apl dungeon show` must not import LangChain or LangGraph: import them lazily inside the
  `run` and `report` code paths.
- **Agents MUST NOT write graph logic in `src/apl/arch/`** (Constitution, Development Workflow).
  T034 is the experimenter's task; `/speckit-implement` stops there and waits.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1–US4)

## Path Conventions

Single project: `src/apl/` and `tests/` at the repository root, as in plan.md.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies, packages and the test safety net

- [ ] T001 Add the runtime dependencies with `uv add "langgraph>=1.2.18,<1.3" "langchain>=1.4.7,<2" "langchain-openai>=1.7.3,<2"` (updates `pyproject.toml` and `uv.lock`); run `uv sync` and confirm `uv run apl dungeon show --level L1 --seed 1000` still works
- [ ] T002 [P] Create the packages `src/apl/runner/__init__.py` (docstring: "Runner side: settings, runs, results and reports. Architectures must not import this package."), `src/apl/arch/__init__.py` (docstring only: "Architectures, written by the experimenter. Each module defines play(kit)."), `tests/runner/__init__.py` and `tests/arch/__init__.py` (empty). Creating `src/apl/arch/` activates `test_architectures_import_only_the_agent_surface`; confirm it passes
- [ ] T003 [P] Create `.env.example` listing every setting of data-model "Settings" with a one-line comment each and no values for secrets (`OPENAI_API_KEY=`), and the defaults commented out; confirm `.gitignore` ignores `.env` but not `.env.example`
- [ ] T004 Create `tests/conftest.py` with an autouse fixture that, for every test: (a) replaces `socket.socket.connect`, `socket.socket.connect_ex` and `socket.create_connection` with functions raising `RuntimeError("network access is blocked in tests")` via `monkeypatch`; (b) sets `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` to `"test-key-not-real"`; (c) deletes every `APL_*` variable from the environment and sets `APL_ENV_FILE` to a path under `tmp_path` that does not exist, so the real `.env` (which holds the API key) is never read. Run `uv run pytest` and confirm the M1 suite still passes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The M1 extension, settings, the kit, the meter, the registry and the test doubles
that every story builds on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Phase 2 ⚠️ (write first, they must fail)

- [ ] T005 [P] Extend `tests/dungeon/test_env.py` and `tests/dungeon/test_frames.py` for research R5: `Episode.unknown("open")` returns `ok: false` with code `unknown_tool` and a message naming the tool and listing look, move, take and use; it counts one step and one invalid action; it is logged as `{"tool": "unknown", "args": ["open"]}`; after the episode ended it returns `episode_over` without a step; `Action.parse({"tool": "unknown", "args": ["open"]})` works and `Action("unknown", ())` raises; a log containing an unknown call replays through `build_frames` with `expected_results` and matches; the text map step table shows `unknown open`
- [ ] T006 [P] Write `tests/runner/test_settings.py` for `apl.runner.settings` (data-model "Settings"): defaults (`model` `openai:gpt-6-luna`, `temperature` and `reasoning_effort` `None`, `token_cap` 600000, `max_retries` 4, `timeout_s` 120, prices `None`); each variable is read; `.env` parsing (`KEY=VALUE`, `#` comment lines, blank lines, values in single or double quotes, `export ` prefix ignored) from the file named by `APL_ENV_FILE`; real environment variables win over `.env`; invalid values raise `ValueError` naming the variable for each rule: "float ≥ 0 when set" (temperature), "non-empty string when set" (reasoning effort), "int > 0" (token cap), "int ≥ 0" (retries), "number > 0" (timeout), "USD per 1M tokens, ≥ 0; both or neither" (prices); `record()` gives `"provider default"` for unset temperature and reasoning effort; `required_key_var("openai:gpt-6-luna") == "OPENAI_API_KEY"`, `"anthropic:x"` → `"ANTHROPIC_API_KEY"`, other providers → `None`
- [ ] T007 [P] Write `tests/runner/test_kit.py` for `apl.kit` (contracts/kit.md), using a hand-built or generated dungeon and a real `Episode`:
  - `TOOL_SCHEMAS` has exactly the four tools with the parameters in the contract (`move.direction` an enum of the four directions, `use` with `item` and `direction`), and each description says that every call costs a step;
  - `BASE_PROMPT` contains no digit characters (so no budget or length can leak) and mentions the exit, steps, keys and JSON results;
  - `prompt_fingerprint()` is 12 hex characters, stable across calls, and changes if a schema description changes (monkeypatch);
  - the tool node runs two calls of one turn in order (a move then a take: the take sees the new room), returns one `ToolMessage` per call with the result JSON as content, the call's id and name, and `status="error"` for a failed result;
  - malformed arguments: `move` with no args → `invalid_direction`; `move` with `{"direction": 3}` → called with `"3"` → `invalid_direction`; extra args are dropped; `take` with none → `no_such_item`; each counts one step;
  - an unknown tool name → `unknown_tool`, one step;
  - when a call ends the episode (move into the exit), the node raises `EpisodeEnded` and later calls of that turn are not in the episode log;
  - when the episode has already ended before the node runs, it raises `EpisodeEnded` and logs nothing;
  - it accepts a dict state `{"messages": [...]}` and an object with a `messages` attribute;
  - `build_kit(...)` returns a `Kit` whose `start` is the JSON of `AgentTools(episode).start.to_dict()`, `recursion_limit == 1000`, and no public attribute holds the `Episode` or `AgentTools`
- [ ] T008 [P] Write `tests/runner/test_meter.py` for `apl.runner.meter` using the scripted model (T011): every model call increments `llm_calls`; tokens add up from `usage_metadata`; a call without usage sets `usage_missing`; passing `token_cap` sets `token_cap_hit` and stops the episode (`end_reason == "stopped"`); a model call after the episode ended raises `EpisodeEnded` and is not counted; the meter still fires after `bind_tools(...)` and after `.with_config(callbacks=[])` (research R3); the transcript stores each distinct message once, each call's `input` as indices, `output` index, `usage` (or `None`) and `latency_s`, and `to_dict()` matches contracts/results.md "`*.conversation.json`"

### Implementation for Phase 2

- [ ] T009 Implement the R5 extension of M1 so T005 passes: `ErrorCode.UNKNOWN_TOOL = "unknown_tool"` in `src/apl/dungeon/results.py`; `Tool` gains `"unknown"` and `_ARITY["unknown"] = 1` in `src/apl/dungeon/model.py`; `Episode.unknown(name: str) -> ToolResult` in `src/apl/dungeon/env.py` through `_call(Action("unknown", (name,)), ...)` returning `ToolResult.failure(ErrorCode.UNKNOWN_TOOL, f"There is no tool named {name!r}. The tools are look, move, take and use.")`; `case "unknown": return episode.unknown(*action.args)` in `frames.call` in `src/apl/dungeon/frames.py`. `AgentTools` stays unchanged (`test_agent_tools_expose_only_the_four_tools` must still pass)
- [ ] T010 Implement `src/apl/runner/settings.py` so T006 passes: frozen `Settings` with the fields and defaults of data-model "Settings"; `load_settings(environ: Mapping[str, str] | None = None) -> Settings` that parses the `.env` file named by `APL_ENV_FILE`, looked up in `environ` first and then in `os.environ` (so a test passing its own `environ` dict still gets the conftest's harmless path), defaulting to `.env` in the current directory (a missing file is fine), and lets `environ` (default `os.environ`) win over the file; `Settings.record() -> dict[str, object]` (the `settings` object of `run.json`, with `prompt_fingerprint` from `apl.kit.prompt_fingerprint()`); `required_key_var(model: str) -> str | None`. Do not import LangChain here
- [ ] T011 [P] Write the test doubles in `tests/runner/scripted.py`:
  - `ScriptedChatModel(BaseChatModel)`, driven by `strategy: Callable[[list[BaseMessage]], AIMessage]`. `_generate` returns that message, with `usage_metadata` from a configurable `usage(messages) -> dict | None` (default: input = number of messages × 10, output = 5). `bind_tools` returns `self.bind()`, and `_llm_type` is `"scripted"`. Tool call ids are unique (`call_<n>`).
  - Strategies:
    - `replay_solution(dungeon)`: the next solution action as a tool call, chosen by counting the `ToolMessage`s seen so far.
    - `text_answer()`
    - `bump_wall(direction)`: always `move` toward a wall.
    - `two_calls_per_turn(dungeon)`
    - `unknown_tool()`
    - `raise_error(exc)`
  - `FakeProviderError(Exception)` with a `status_code: int` attribute, for research R8 classification.
  - `scripted_factory(strategy, usage=...)`: a model factory with the runner's signature (T018) that returns a `ScriptedChatModel` with the given callbacks.
- [ ] T012 [P] Write the test-only architecture `tests/runner/loop_arch.py`: `play(kit)` as a plain Python `while` loop (no `StateGraph`; research R14). It binds `kit.model.bind_tools(kit.tools)`, starts from `[SystemMessage(kit.base_prompt), HumanMessage(kit.start)]`, invokes the model, returns when the reply has no tool calls, and otherwise appends the reply and `kit.tool_node({"messages": [...]})["messages"]`. Also `def crash(kit): raise ValueError("boom")`
- [ ] T013 Implement `src/apl/kit.py` so T007 passes (contracts/kit.md):
  - Constants: `BASE_PROMPT` (the content listed under "Base prompt", no digits), `TOOL_SCHEMAS` (four OpenAI-style function dicts `{"type": "function", "function": {"name", "description", "parameters"}}`) and `RECURSION_LIMIT = 1000`.
  - `prompt_fingerprint() -> str`: SHA-256 over the canonical JSON (`sort_keys=True`, `separators=(",", ":")`) of `{"prompt": BASE_PROMPT, "tools": TOOL_SCHEMAS}`, first 12 hex characters.
  - `class EpisodeEnded(Exception)`.
  - Frozen `Kit` with fields `model`, `tools`, `tool_node`, `base_prompt`, `start` and `recursion_limit`.
  - `build_kit(episode: Episode, model: BaseChatModel) -> Kit`. Its `tool_node` is a closure that does the following:
    - It raises `EpisodeEnded` if the episode already ended.
    - Otherwise it runs each tool call in order with the normalization of research R5: missing argument `""`, non-string as `json.dumps(value)`, extra arguments dropped, unknown names via `episode.unknown`. Known tools go through an `AgentTools(episode)`.
    - It builds a `ToolMessage` per call, with `json.dumps(result.to_dict())`, `status="error"` when not ok.
    - It raises `EpisodeEnded` right after a call that ends the episode.
    - It returns `{"messages": [...]}`.

  `apl.kit` may import `apl.dungeon.env` and `apl.dungeon.tools`, but nothing from `apl.runner`.
- [ ] T014 Implement `src/apl/runner/meter.py` so T008 passes (data-model "Meter", "Transcript"): `Meter(BaseCallbackHandler)` with `raise_error = True`, `on_chat_model_start` (guard, count, record input), `on_llm_end` (record output, usage from `response.generations[0][0].message.usage_metadata`, latency since the matching start keyed by `run_id`, add tokens, stop the episode and set `token_cap_hit` once `input_tokens + output_tokens > token_cap`); `Transcript` deduplicating messages by canonical JSON of `langchain_core.messages.message_to_dict`, with `to_dict()`
- [ ] T015 Implement `src/apl/runner/registry.py`: `ARCHITECTURES: dict[str, str] = {"react": "apl.arch.react"}`; `is_written(name) -> bool` via `importlib.util.find_spec`; `load(name) -> Callable[[Kit], None]` importing the module and returning its `play`, raising `ValueError` with "unknown architecture … (registered: react)" or "architecture react is not written yet (src/apl/arch/react.py)"

**Checkpoint**: `uv run pytest tests/dungeon tests/runner/test_settings.py tests/runner/test_kit.py tests/runner/test_meter.py` passes.

---

## Phase 3: User Story 1 - Plan a run without spending anything (Priority: P1) 🎯 MVP

**Goal**: `apl run` without `--execute` prints the matrix and real upper bounds, and does nothing
else.

**Independent Test**: Plan several run descriptions with the network blocked and a dummy key
present; compare with hand-worked counts; confirm no file is written.

### Tests for User Story 1 ⚠️ (write first, they must fail)

- [ ] T016 [P] [US1] Write `tests/runner/test_spec.py` for `apl.runner.spec` (data-model "RunSpec"):
  - Matrix order is architecture, level, seed, repeat, with repeats starting at 1. "A1 on L2, dev seeds, 3 repeats" gives 30 episodes (US1/AC1).
  - `all` expands to L1, L2, L3.
  - `--limit 2` takes the first two dev seeds. `--only 1000,1004` takes those seeds.
  - These are refused: `--only 5` (not in the set), `--limit 0`, `--limit 11`, `--limit` combined with `--only`, duplicate levels or architectures, and `repeats` 0.
  - Upper bounds:
    - model calls are Σ budgets + episodes. For react, L1–L3 and dev seeds 1000 and 1001 this is 228.
    - tokens are episodes × token cap.
    - cost is tokens × max(price_in, price_out) / 1e6. With prices 0.10 and 0.50 it is $1.80, and `None` without prices.
- [ ] T017 [P] [US1] Write the dry-run tests in `tests/runner/test_cli_run.py`. Each runs `main([...])` in a `tmp_path` working directory with `capsys`:
  - The output contains these lines from contracts/cli.md: `episodes       6`, `model          openai:gpt-6-luna`, `temperature    provider default`, `model calls    228` and `tokens         3,600,000`.
  - With `APL_PRICE_INPUT=0.10` and `APL_PRICE_OUTPUT=0.50`, the cost line shows `$1.80`. Without prices it shows the "no estimate" line (US1/AC3).
  - Dev seeds print `development only, must not be reported` and test seeds print `for reporting` (US1/AC4).
  - Nothing is created in `tmp_path`, and the network guard is never hit (SC-001).
  - `--arch nope` and `--level L9` exit 2 with the valid choices (US1/AC2).
  - `--arch react`, while `src/apl/arch/react.py` does not exist (monkeypatch `registry.is_written` to `False`), prints the plan with `(not written yet)` and exits 0.

### Implementation for User Story 1

- [ ] T018 [US1] Implement `src/apl/runner/spec.py` so T016 passes: frozen `RunSpec` and `EpisodeKey(arch, level, seed, repeat)`; `RunSpec.build(archs, levels, seed_set, limit, only, repeats) -> RunSpec` with every rule of data-model "RunSpec" quoted in its `ValueError` messages; `episodes()`; `upper_bounds(settings) -> Bounds(calls, tokens, cost | None)` generating the dungeons to sum budgets; `format_plan(spec, settings, written: Mapping[str, bool]) -> str` producing the block in contracts/cli.md (numbers with thousands separators, cost as `$X.XX (at $in / $out per 1M tokens)`)
- [ ] T019 [US1] Add the `run` subcommand to `src/apl/cli.py` per contracts/cli.md (`--arch`, `--level`, `--seeds`, `--limit`, `--only`, `--repeats`, `--execute`); without `--execute`, load settings, build the spec, print `format_plan` and return 0; argument and settings errors print `apl: <message>` to stderr and return 2. Import `apl.runner` modules inside the handler so `apl dungeon show` stays LangChain-free. T017 passes

**Checkpoint**: `uv run apl run --arch react --level all --seeds dev --limit 2` prints the plan;
`results/` is untouched.

---

## Phase 4: User Story 2 - Run episodes and record structured results (Priority: P2)

**Goal**: `--execute` plays every episode, writes rows, outcome and conversation files and the
settings record, and handles provider failures and interruptions.

**Independent Test**: Run small matrices with the scripted model and the loop architecture; check
rows, files, counts and error handling.

### Tests for User Story 2 ⚠️ (write first, they must fail)

- [ ] T020 [P] [US2] Write `tests/runner/test_results.py` for `apl.runner.results`:
  - `EpisodeRow.completed(...)` derives `efficiency = round(optimal / steps, 3)` on success and `None` on failure, and `tool_calls = len(outcome.log)`. Tokens are `None` when `usage_missing`. `budget_hit` and `token_cap_hit` are passed through.
  - `EpisodeRow.failed(...)` sets `status: "error"`, the error text, `optimal_steps` and `budget`, and `null` for the outcome fields (contracts/results.md).
  - `to_dict()` key order matches the contract example.
  - `EpisodeRow.parse` round-trips and rejects a wrong type, an unknown `status` or a missing field with `ValueError` naming the field.
  - `RunRecord` round-trips through JSON with every field of data-model "RunRecord".
- [ ] T021 [P] [US2] Write `tests/runner/test_run.py` for `apl.runner.run.execute(...)`. It uses `scripted_factory`, an injected architecture mapping (`{"loop": loop_arch.play, "crash": loop_arch.crash}`) and `results_dir=tmp_path`. Cases:
  - `replay_solution` on dev seed 1000 of L1, L2 and L3: success, steps = optimal, efficiency 1.0, `invalid_actions` 0, `llm_calls` = steps (the last move ends the episode inside the tool node, so no final model call), tokens match the scripted usage (US2/AC1, SC-002).
  - `text_answer`: `stopped`, 0 steps, failure (US2/AC2).
  - `bump_wall`: `budget_hit`, `llm_calls == budget`, and no model call after the end (US2/AC3, SC-003).
  - Usage of 400,000 per call: `token_cap_hit`, `stopped`, `llm_calls == 2` (US2/AC4, SC-003).
  - `crash`: `stopped`, `arch_error == "ValueError: boom"`, scored as a failure.
  - `raise_error(FakeProviderError(status_code=429))` on the second of two episodes: that row has `status: "error"`, and the run continues and completes.
  - `status_code=401`: the run stops, exit code 3, `completed: false`, and earlier rows are kept.
  - `KeyboardInterrupt` raised by the strategy: rows kept, `completed: false`, and it re-raises.
  - Every `*.outcome.json` replays with `parse_route_file(...).frames(dungeon)` to the row's steps and end reason (US2/AC5, SC-004).
  - `*.conversation.json` exists with `len(calls) == llm_calls`.
  - `run.json` has every field of contracts/results.md, including `prompt_fingerprint` and `code.dirty` (US2/AC6).
  - Two runs in the same second get distinct folders (`-2` suffix).
  - Average runner overhead per episode with the scripted model over all dev dungeons of L1 is under 1 s (SC-010).
- [ ] T022 [P] [US2] Add execute-path tests to `tests/runner/test_cli_run.py`:
  - `--execute` with `OPENAI_API_KEY` removed exits 2 with `OPENAI_API_KEY is not set` and creates no folder.
  - `--execute` for an architecture that is not written yet exits 2.
  - `--execute` with the scripted factory and loop architecture monkeypatched in prints one progress line per episode in the contract's format and the run folder path.

### Implementation for User Story 2

- [ ] T023 [US2] Implement `src/apl/runner/results.py` so T020 passes: `EpisodeRow` (frozen, fields and order of contracts/results.md) with `completed`, `failed`, `to_dict`, `parse`; `RunRecord` with `to_dict`/`parse`; `append_row(path, row)` (append one JSON line and flush); `write_json(path, data)` (UTF-8, indent 2)
- [ ] T024 [US2] Implement `src/apl/runner/episode.py`: `play_episode(key, settings, play, model_factory) -> EpisodeResult(row, outcome | None, transcript)`. It does the following:
  - Generates the dungeon and starts the episode.
  - Creates the `Meter` and the model with `model_factory(settings, callbacks=[meter])`.
  - Builds the kit, times `play(kit)`, and catches `EpisodeEnded`.
  - On a provider exception (research R8), retries are exhausted; it re-raises a `PermanentProviderError` for status 400, 401, 403, 404 or 422 and otherwise returns an error row.
  - Any other exception becomes `episode.stop()` plus `arch_error = f"{type(e).__name__}: {e}"`.
  - It calls `episode.stop()` if `play` returned early, and builds the row.

  Provider exceptions are recognized as `openai.APIError` instances or any exception with an int `status_code`.
- [ ] T025 [US2] Implement `src/apl/runner/run.py` so T021 passes:
  - `default_model_factory(settings, callbacks)` calls `init_chat_model(settings.model, callbacks=callbacks, max_retries=..., timeout=...)`. It adds `temperature` and `reasoning_effort` only when set.
  - `execute(spec, settings, *, model_factory=default_model_factory, architectures=None, results_dir=Path("results"), on_episode=None) -> RunOutcome` does the following:
    - Creates the run folder with `mkdir(parents=True, exist_ok=False)`, named `YYYYMMDD-HHMMSS-<arch>[+<arch>]` with a `-2`, `-3`… suffix on a clash.
    - Writes `run.json` with `completed: false`.
    - Plays the episodes in order. After each one it writes `episodes/<arch>-<level>-<seed>-r<repeat>.outcome.json` (completed episodes only), `.conversation.json` (if any call was made), and appends the row.
    - At the end it sets `completed: true` and `ended`.
    - On `PermanentProviderError` it stops and returns exit code 3.
    - On `KeyboardInterrupt` it leaves `completed: false` and re-raises.
  - `code` comes from `git rev-parse HEAD` and `git status --porcelain`, run via `subprocess`, or `null` without git. `versions` come from `importlib.metadata` for `langgraph`, `langchain`, `langchain-core`, `langchain-openai`, plus the Python version.
- [ ] T026 [US2] Wire `--execute` into `src/apl/cli.py`:
  - Check `required_key_var(settings.model)` and refuse with exit 2 if it isn't set. Refuse architectures that are not written yet with exit 2.
  - Call `execute` with an `on_episode` callback that prints `[i/n] <arch> <level> <seed> r<repeat>  <end>  steps <s>/<budget> (optimal <o>)  calls <c>  tokens <t>  <latency>s` (for an error row: `error  <message>`).
  - Print the folder path.
  - Return 0, 3, or 130 on `KeyboardInterrupt`.

  T022 passes.

**Checkpoint**: `uv run pytest tests/runner` passes except `test_report.py`; a scripted run
produces a complete run folder.

---

## Phase 5: User Story 3 - Read a report (Priority: P3)

**Goal**: `apl report` turns one or more compatible runs into the markdown tables of
contracts/results.md.

**Independent Test**: Build reports from hand-written run folders and check every figure by hand.

### Tests for User Story 3 ⚠️ (write first, they must fail)

- [ ] T027 [P] [US3] Write `tests/runner/test_report.py`. A helper writes run folders (`run.json` plus `episodes.jsonl`) into `tmp_path` from hand-written rows. Cases:
  - **Group statistics:** one run, react, L1 and L2, 2 seeds, 3 repeats, with chosen numbers. Every figure is checked against a hand calculation written as a comment: success rate, median efficiency over successes, invalid per episode, budget-hit rate, token-cap rate, median calls, median input and output tokens, median latency (US3/AC1, SC-005).
  - **Spread:** min and max of the per-repeat success rate and median efficiency (US3/AC2).
  - **Combining runs:** two runs with different architectures and equal settings give one table (US3/AC3). A combination is refused naming each differing field among `seed_set`, `model`, `temperature`, `reasoning_effort`, `token_cap` and `prompt_fingerprint`, one case per field (US3/AC4, SC-006). Differing seed lists add a note.
  - **Errors and gaps:** error rows are excluded from scores and listed in the error section (US3/AC5). Rows with `null` tokens are skipped in token medians and counted in the notes. A median with no values shows `—`. An incomplete run is noted.
  - **Headers:** a dev run has the development header and a test run the test header (US3/AC6).
  - **Bad input:** a folder without `run.json`, or with a malformed row, raises `ValueError` naming the file and line.
- [ ] T028 [P] [US3] Add report CLI tests to `tests/runner/test_cli_run.py`: `apl report <run>` prints the report and writes `<run>/report.md`; with two runs it writes `results/report-<timestamp>.md` (run in `tmp_path`); incompatible runs exit 2 with `apl: cannot combine runs: ...`

### Implementation for User Story 3

- [ ] T029 [US3] Implement `src/apl/runner/report.py` so T027 passes (data-model "Report", contracts/results.md "Report"): `load_run(path) -> LoadedRun`, `check_compatible(runs) -> list[str]` (notes; raises `ValueError` naming differing fields), `group_stats`, `spread`, `render(runs) -> str` using `statistics.median`, percentages without decimals, efficiency with 2 decimals, numbers with thousands separators, latency with one decimal and `s`, `—` for missing; sections and notes only when needed; rows sorted by architecture, then level
- [ ] T030 [US3] Add the `report` subcommand to `src/apl/cli.py` (contracts/cli.md) and call the report at the end of a completed `apl run --execute` (print it and write `<run>/report.md`). T028 passes

**Checkpoint**: `uv run pytest tests/runner` passes; a scripted run ends with a printed report.

---

## Phase 6: User Story 4 - Play A1 ReAct (Priority: P4)

**Goal**: The experimenter's A1 plugs in through the kit, passes its scripted tests and the
boundary check, and one small paid run produces a report.

**Independent Test**: A1 with the scripted model on one dev dungeon per level; then the paid run.

### Tests for User Story 4 ⚠️ (write first)

- [ ] T031 [P] [US4] Extend `tests/dungeon/test_boundary.py` for research R15:
  - `ALLOWED` becomes `{"apl.kit", "apl.dungeon.tools", "apl.dungeon.results"}`. Any other `apl.` import from `src/apl/arch/` is forbidden, including `apl.runner` and `apl.dungeon` internals.
  - Imports of `openai`, `anthropic`, `langchain_openai`, `langchain_anthropic`, `langchain.chat_models` and `langchain_core.language_models`, and their submodules, are forbidden.
  - Any use of the names `init_chat_model`, `ChatOpenAI` or `ChatAnthropic` (as `ast.Name` or `ast.Attribute`) is forbidden.
  - Extend `test_boundary_scan_catches_forbidden_imports` with files that do each of these, plus an allowed file importing `apl.kit`, `langgraph.graph` and `langchain_core.messages`. Keep the existing cases and their sorted expected list (SC-007).
- [ ] T032 [P] [US4] Write `tests/arch/test_react.py`, skipped with `pytest.skip("src/apl/arch/react.py is not written yet")` when `registry.is_written("react")` is false. It plays `apl.arch.react.play` through `play_episode` with `scripted_factory`:
  - `replay_solution` on dev seed 1000 of L1, L2 and L3 succeeds with efficiency 1.0 (US4/AC1, SC-008).
  - `text_answer` ends as `stopped` with no `arch_error` (US4/AC2).
  - `bump_wall` on L1 ends with `budget_hit` and no `arch_error`, which shows the recursion limit is passed through.
  - The model receives `kit.base_prompt` as the first system message and `kit.start` in the first user message.

### Implementation for User Story 4

- [ ] T033 [US4] Update the boundary scanner in `tests/dungeon/test_boundary.py` so T031 passes, and update the rule in `AGENTS.md` ("Architectures ... may import only `apl.kit`, `apl.dungeon.tools` and `apl.dungeon.results`, and must use `kit.model` instead of creating a model (enforced by a test)")
- [ ] T034 [US4] ⚠️ **Experimenter task, agents MUST NOT do it** (Constitution, Development Workflow): write `src/apl/arch/react.py` with `play(kit)` per contracts/kit.md "A1 ReAct": a `StateGraph` over `MessagesState`, a model node using `kit.model.bind_tools(kit.tools)`, `kit.tool_node` as the tool node, a conditional edge (`tools_condition` or your own) back to the model while there are tool calls, invoked with `[SystemMessage(kit.base_prompt), HumanMessage(kit.start)]` and `config={"recursion_limit": kit.recursion_limit}`. `/speckit-implement` stops here and waits
- [ ] T035 [US4] Run `uv run pytest tests/arch tests/dungeon/test_boundary.py` and fix any failure outside `src/apl/arch/` (report failures inside it to the experimenter instead of editing the graph)
- [ ] T036 [US4] Small paid run (SC-009): the experimenter runs `uv run apl run --arch react --level all --seeds dev --limit 2 --execute` (an agent may start it only after the experimenter explicitly approves that run). Confirm 6 rows, 12 episode files, `completed: true` and the printed report; then open one episode with `apl dungeon show --route .../react-L2-1001-r1.outcome.json --html` (quickstart steps 4 and 5)

**Checkpoint**: plan.md's M2 done criterion is met: one dry run and one small paid run produce a
report.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and the final gate

- [ ] T037 [P] Add a test in `tests/runner/test_cli_run.py` that runs `python -c "import apl.cli, sys; sys.exit('langchain' in sys.modules or 'langgraph' in sys.modules)"` in a subprocess and asserts exit 0, so `apl dungeon show` stays free of LangChain (plan.md Constraints)
- [ ] T038 [P] Add one line to `specs/001-dungeon-environment/contracts/tools.md` under the error codes: "M2 adds `unknown_tool` for calls to a tool that does not exist (see specs/002-runner-react/contracts/kit.md)."
- [ ] T039 [P] Update `README.md`: status line (M2: runner, results, report; A1 when written), a "Run an experiment" block with the dry run, the `--execute` run and `apl report` from quickstart.md, and the `.env` variables (`APL_MODEL`, `OPENAI_API_KEY`, optional `APL_TEMPERATURE`, `APL_REASONING_EFFORT`, `APL_TOKEN_CAP`, `APL_PRICE_INPUT`, `APL_PRICE_OUTPUT`); remove "(planned, M2)" from the runner line in the layout
- [ ] T040 Run the free steps of `specs/002-runner-react/quickstart.md` (1, 2, 6 with a scripted run folder) and all four checks: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none. T004 must exist before any new test runs.
- **Foundational (Phase 2)**: depends on Setup and blocks every story.
- **US1 (P1)**: after Foundational.
- **US2 (P2)**: after Foundational; uses `spec.py` from US1 (T018) for `RunSpec` and `EpisodeKey`.
- **US3 (P3)**: tests and `report.py` need only the row format (T023); T030's hook into `apl run`
  needs US2.
- **US4 (P4)**: T031–T033 can start after Foundational. T034 (experimenter) needs Foundational;
  T035 needs T034 and US2's `play_episode` (T024); T036 needs US1–US3 and T034.
- **Polish**: after all stories (T036 may come later, when the experimenter runs it).

```text
Setup → Foundational ─┬─ US1 ── US2 ─┬─ US3 ─┐
                      │              └───────┴─ T035, T036 ── Polish
                      └─ US4 tests (T031–T033), T034 (experimenter) ─┘
```

### Within Each Story

Tests first, and they must fail (A1 tests skip until T034). Then implementation in task order.
The story is done when its tests pass.

### Parallel Opportunities

- **Setup:** T002 and T003 beside T001; T004 after T001.
- **Foundational:** tests T005–T008 together; T011 and T012 beside them; then T009, T010 in
  parallel, then T013, T014, T015.
- **US1:** T016 and T017 together.
- **US2:** T020–T022 together.
- **US3:** T027 and T028 together; T029 can start once T023 exists.
- **US4:** T031 and T032 together, and both can run beside US1–US3. The experimenter can write
  T034 as soon as Phase 2 is done.
- **Polish:** T037–T039 together.

---

## Parallel Example: Phase 2

```bash
# Tests and test doubles first, together:
Task: "Extend tests/dungeon/test_env.py and test_frames.py for unknown tools (T005)"
Task: "Write tests/runner/test_settings.py (T006)"
Task: "Write tests/runner/test_kit.py (T007)"
Task: "Write tests/runner/test_meter.py (T008)"
Task: "Write tests/runner/scripted.py (T011)"
Task: "Write tests/runner/loop_arch.py (T012)"
```

## Parallel Example: User Stories 3 and 4

```bash
# Once the row format exists, the report and the boundary work don't touch each other:
Task: "US3: T027–T029 (report)"
Task: "US4: T031–T033 (boundary, A1 tests, AGENTS.md)"
Task: "Experimenter: T034 (src/apl/arch/react.py)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup, then Phase 2 Foundational.
2. Phase 3 (US1): the dry run.
3. **Stop and validate**: `uv run apl run --arch react --level all --seeds dev --limit 2` prints
   the plan and writes nothing.

### Incremental Delivery

1. US1: plan runs safely.
2. US2: execute with the scripted model; run folders are complete.
3. US3: reports from those folders.
4. US4: the experimenter's A1 passes its tests; one small paid run and its report close M2.

---

## Notes

- [P] tasks touch different files and don't depend on incomplete tasks.
- The real `.env` is never read by tests (T004), and no file under `results/` is committed.
- A1 (`src/apl/arch/react.py`) is written by the experimenter only. If an A1 test fails, report it;
  do not edit the graph.
- Commit after each phase or logical group, only when the user asks.
