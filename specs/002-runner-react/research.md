# Research: Runner, Results Format, Report and A1 ReAct

Technical Context had three open items: the library versions, the parameters `gpt-6-luna`
accepts, and how LangGraph and LangChain behave around tools, callbacks and errors. The
library behavior was checked with a probe script against the pinned versions, installed in a
scratch environment (no network calls to a provider, no paid calls). Nothing is left as NEEDS
CLARIFICATION.

## R1. Libraries and versions

- **Decision**: Add three runtime dependencies: `langgraph>=1.2.18,<1.3`, `langchain>=1.4.7,<2`
  (for `init_chat_model`) and `langchain-openai>=1.7.3,<2` (the provider for the default model).
  `langchain-core` (1.7.3) and `openai` (3.41.0) come in through them and are declared too,
  because the runner imports them directly (callbacks and provider error types). Other providers are
  added by installing their LangChain package; no code changes.
- **Rationale**: These are the current releases on PyPI (2026-10-30), and the constitution fixes
  LangGraph 1.2.x and `init_chat_model`. The probe ran on exactly these versions.
- **Alternatives considered**: Calling the OpenAI SDK directly, as rag-stack does (it would skip
  `init_chat_model` and tie the lab to one provider); also depending on `langchain-anthropic` now
  (not needed until someone switches provider).

## R2. Model settings for `gpt-6-luna`

- **Decision**: The shared settings carry `APL_MODEL` (default `openai:gpt-6-luna`),
  `APL_TEMPERATURE` and `APL_REASONING_EFFORT`. Both are unset by default, and an unset value is
  not sent, so the provider's default applies and is recorded as `"provider default"`. The two
  are treated together as the sampling settings: they go into the settings record and the
  report's compatibility check alongside the temperature (FR-001, FR-020, FR-031).
- **Rationale**: `gpt-6-luna` is a reasoning model with effort levels from `none` to `max`,
  defaulting to `medium`. Its temperature only applies when reasoning is off
  (`reasoning_effort="none"`); otherwise it is dropped or refused. Pinning a temperature by
  default would therefore either fail or force reasoning off. Leaving both at the provider
  default is identical for every architecture, which is what Principle I needs, and the
  experimenter can still pin both. Source: the LiteLLM day-0 notes for GPT-6 Sol and Luna;
  OpenAI's own reference should be checked before pinning values.
- **Price**: the same source lists $0.10 per million input tokens and $0.50 per million output
  tokens (up to 272K context). Prices stay optional configuration (`APL_PRICE_INPUT`,
  `APL_PRICE_OUTPUT`, USD per million tokens); the quickstart shows these values for the
  experimenter to confirm.
- **Alternatives considered**: `temperature=0` with `reasoning_effort="none"` (most repeatable,
  but it turns off the model's reasoning, which changes what is being measured); validating
  provider-specific parameter rules in the runner (a moving target; the provider's own error is
  clearer, and R8 stops the run on it).

## R3. Counting model calls and tokens, and stopping after the end

- **Decision**: One callback handler per episode, the **meter**, attached to the model through the
  model's own `callbacks` field when the runner creates it. It has `raise_error = True`.
  - `on_chat_model_start` refuses the call (raises `EpisodeEnded`) if the episode has already
    ended, otherwise counts it and notes the input messages.
  - `on_llm_end` reads `usage_metadata` from the returned message, adds the tokens, notes the
    output, and ends the episode as stopped with `token_cap_hit` once the total passes the cap.
- **Probe results**:
  - Callbacks attached with `model.with_config(callbacks=...)` are **lost** by `bind_tools`
    (LangChain 1.4 returns a new `_ChatModelBinding` with an empty config). Callbacks set on the
    model object survive `bind_tools`, fire on every call, and stay even if an architecture calls
    `with_config(callbacks=[])`.
  - An exception raised in `on_chat_model_start` with `raise_error = True` propagates out of
    `graph.invoke` unchanged. LangChain logs a one-line "Error in ... callback" message, which is
    harmless.
  - `GenericFakeChatModel` passes `usage_metadata` through to `on_llm_end`, so the scripted model
    in tests is metered exactly like the real one.
- **Rationale**: Measuring in the model object means every architecture is measured the same way,
  whatever its graph looks like (FR-023). The guard in the same place makes FR-009 hold by
  construction: after the end, no model call can even start. Total tokens per episode are
  input plus output summed over calls; reasoning tokens are part of the output count.
- **Alternatives considered**: Asking architectures to report their own usage (not uniform, easy
  to get wrong); wrapping the model in a proxy class (has to forward `bind_tools`,
  `with_structured_output` and more, so it breaks easily); LangChain's
  `UsageMetadataCallbackHandler` (counts tokens but cannot enforce the cap or the guard).

## R4. Executing tool calls: a shared tool node instead of `ToolNode`

- **Decision**: The shared setup provides `kit.tool_node`, a graph node that architectures add
  with `add_node`. It reads the last AI message's tool calls and runs them **one after another**
  through the episode, then returns one `ToolMessage` per call with the M1 result as JSON
  (`status="error"` for a failed result). `kit.tools` holds the four tool schemas for
  `bind_tools`; they cannot be executed on their own.
- **Probe results**: LangGraph's prebuilt `ToolNode`:
  - runs the tool calls of one turn **in parallel** (two calls finished in reverse order in the
    probe), which would make the order of moves random and the episode unsafe;
  - answers a call to an unknown tool, or a call with missing arguments, by itself, without
    calling the tool, so the step would not be counted.
- **Rationale**: Both behaviors break Principle III and FR-003. Tool execution is the same for
  every architecture, so it belongs to the shared setup, like the tool descriptions. The graph
  still decides when tools run; `langgraph.prebuilt.tools_condition` works with the shared node
  for routing.
- **Alternatives considered**: `ToolNode` with `max_concurrency=1` (fixes the order but still
  skips counting invalid calls); a `wrap_tool_call` hook (not called for unknown tool names).

## R5. Invalid tool calls in the M1 environment

- **Decision**: The shared tool node maps every call onto the episode:
  - A known tool with missing or non-string arguments is called with each missing argument as
    `""` and each non-string argument as its JSON text; extra arguments are dropped. The M1
    environment then answers with its usual error (`invalid_direction`, `no_such_item`,
    `not_in_inventory`), one step counted.
  - An unknown tool name is recorded through a new `Episode.unknown(name)` call that counts one
    step and one invalid action and returns the new error code `unknown_tool`. It is logged as
    the action `{"tool": "unknown", "args": ["<name>"]}`, so the log still replays: `Action`
    accepts `unknown` with one argument, and `frames.call` passes it to `Episode.unknown`.
- **Rationale**: Every model call to a tool costs a step (FR-003), and the M1 log stays the single
  source for drawing and replay (FR-024). The change to M1 is additive: one error code, one
  pseudo-action and one episode method. `AgentTools` keeps exactly its four public tools.
- **Alternatives considered**: Not counting invalid calls (breaks Principle III); mapping an
  unknown tool to `look` (logs something that did not happen).

## R6. The architecture interface

- **Decision**: An architecture is a module `apl.arch.<name>` with one function,
  `play(kit: Kit) -> None`. It builds its graph with `StateGraph`, invokes it, and returns.
  The runner's registry maps names to modules (`react` → `apl.arch.react`) and imports them
  lazily; a registered module that does not exist yet is reported as "not written yet".
  `EpisodeEnded` from the meter or the tool node is caught by the runner, so a graph never has to
  handle the end of an episode itself.
- **What `Kit` holds** (contracts/kit.md): `model`, `tools`, `tool_node`, `base_prompt`,
  `start` (the free start-room result as JSON) and `recursion_limit`.
- **Recursion limit**: LangGraph's default `recursion_limit` is 25 super-steps. A ReAct loop
  needs about two per step, and L3 budgets reach 78 steps. `kit.recursion_limit` is a constant
  1,000 for every episode, because a value derived from the budget would leak the shortest
  solution's length (budget = 3 × optimal; Principle II). The step budget remains the real
  limit.
- **Rationale**: `play` leaves the whole graph, its state schema and its invocation to the
  experimenter (Principle III, Development Workflow). The registry lives in `src/apl/runner/`,
  so `src/apl/arch/` contains only files the experimenter writes.
- **Alternatives considered**: `build(kit) -> CompiledGraph`, with the runner invoking it (the
  runner would have to know each graph's input state, which differs per architecture); a
  registry file in `src/apl/arch/` (puts non-graph code into the experimenter's folder).

## R7. How an episode ends, and which failures count against an architecture

- **Decision**:
  | What happened | End reason | Row status | Scored |
  | --- | --- | --- | --- |
  | Exit reached | `exit` | `completed` | yes |
  | Budget used up | `budget` | `completed` | yes |
  | Token cap passed | `stopped`, `token_cap_hit: true` | `completed` | yes |
  | `play` returned before the end | `stopped` | `completed` | yes |
  | `play` raised a non-provider exception (for example `GraphRecursionError` or a bug) | `stopped`, with `arch_error` | `completed` | yes |
  | Provider failed after retries (rate limit, timeout, connection, 5xx) | none | `error` | no |
  | Provider rejected the request permanently (400, 401, 403, 404, 422) | none | the run stops | — |
- **Rationale**: Only failures outside the architecture's control may be excluded from scores
  (FR-029). An architecture that crashes or loops has failed the task, so its episode counts as a
  failure, with the exception text kept for debugging. A 400 is treated as permanent because
  with a 1M-token context and the token cap it means a bad parameter or request shape, which
  would fail every episode the same way.
- **Alternatives considered**: Treating every exception as an infrastructure error (hides
  architecture bugs and inflates success rates).

## R8. Retries

- **Decision**: Use the provider client's own retries: `init_chat_model(..., max_retries=4,
  timeout=120)`. The OpenAI client retries rate limits, timeouts, connection errors and 5xx with
  exponential backoff. When it gives up, the runner classifies the exception by its
  `status_code` (R7): 400, 401, 403, 404 and 422 stop the run; anything else from the provider
  marks the episode as an infrastructure error. Provider exceptions are recognized as
  `openai.APIError` or any exception carrying a `status_code`, so other providers behave alike.
- **Rationale**: The SDK already implements the "fixed number, growing pause" policy (FR-017).
  The values are shared settings (`APL_MAX_RETRIES`, `APL_TIMEOUT_S`) and are recorded.
- **Alternatives considered**: LangChain's `with_retry` (a second retry layer on top of the
  SDK's, so delays would multiply).

## R9. Per-episode token cap

- **Decision**: Default `APL_TOKEN_CAP = 600_000` tokens (input + output, summed over calls).
- **Rationale**: The largest L3 budget across dev and test seeds is 78 steps. A ReAct episode
  that uses the whole budget resends its growing history every turn: roughly 79 calls ×
  (about 800 prompt tokens) plus about 150 tokens of history per turn, summed over turns,
  ≈ 63K + 470K ≈ 530K input tokens, plus reasoning output. 600K lets a full legitimate episode
  finish and stops only runaway ones. At the listed prices that is at most about $0.06 input per
  episode.
- **Alternatives considered**: A cap scaled by the budget (would reveal the budget to anyone
  reading the cap and adds a rule); no cap (plan §8 asks for one).

## R10. Upper bounds in the dry run

- **Decision**:
  - model calls ≤ Σ budgets + episodes (at most one model call per step plus one final answer,
    for single-model architectures; spec Assumptions);
  - tokens ≤ episodes × token cap;
  - cost ≤ tokens × max(input price, output price) / 1,000,000, shown only when prices are set.
- **Rationale**: These are real upper bounds that need no guess about the model's behavior.
  Budgets are computed by generating the dungeons, which is local and takes milliseconds.
- **Alternatives considered**: An "expected" estimate from average tokens per call (looks precise
  but depends on the model and the architecture).

## R11. Settings and the API key

- **Decision**: Settings come from environment variables, with `.env` in the current directory
  (or the file named by `APL_ENV_FILE`, which the tests point at an empty file) read first by a
  small standard-library parser (`KEY=VALUE` lines, `#` comments, optional quotes).
  Variables already set in the environment win. With `--execute`, the provider prefix of
  `APL_MODEL` selects the required key variable (`openai` → `OPENAI_API_KEY`, `anthropic` →
  `ANTHROPIC_API_KEY`); a missing key stops the run before any episode (FR-014). For other
  providers the runner does not check, and a rejected key stops the run on the first call (R8).
- **Fingerprint**: SHA-256 over the canonical JSON of the base prompt and the four tool schemas,
  first 12 hex digits.
- **Rationale**: Nothing beyond a handful of variables is needed, so a dependency on
  `python-dotenv` is not worth it. The key is never written to any results file.
- **Alternatives considered**: `python-dotenv` (a dependency for ten lines); a TOML settings file
  (a second place for the same values).

## R12. Results files

- **Decision**: One folder per run, `results/<YYYYMMDD-HHMMSS>-<arch>[+<arch>...]/`, created with
  `mkdir(exist_ok=False)`; on a clash a `-2`, `-3`… suffix is added. Inside:
  `run.json` (the settings record), `episodes.jsonl` (one row per episode, appended and flushed
  as each episode ends), and `episodes/<arch>-<level>-<seed>-r<repeat>.outcome.json` and
  `.conversation.json`. `results/` is already in `.gitignore`.
- **Conversation format**: each distinct message is stored once in `messages`, and each model call
  lists its input as indices into that list, plus its output index, usage and latency. Storing
  every call's full input would grow with the square of the episode length (about 4 MB for one
  long L3 episode, hundreds of MB for M3).
- **Rationale**: JSONL rows can be appended safely and survive an interrupted run (FR-018).
  The outcome file is exactly the M1 outcome record, so `apl dungeon show --route` reads it
  unchanged (FR-024).
- **Alternatives considered**: SQLite (harder to read by hand); one big JSON file per run (lost on
  interruption).

## R13. Report

- **Decision**: `apl report RUN [RUN ...]` reads `run.json` and `episodes.jsonl` of each run,
  checks compatibility (FR-030, FR-031), and prints a markdown report. With one run it writes
  `<run>/report.md`; with several, `results/report-<YYYYMMDD-HHMMSS>.md`. Rates are shown as
  percentages, medians with `statistics.median`, and a missing value as `—`.
- **Spread**: for each repeat number, success rate and median efficiency are computed over that
  repeat's seeds; the report shows the lowest and highest across repeats (FR-028).
- **Rationale**: Standard library only; every figure can be recomputed by hand from the rows
  (FR-032, SC-005).
- **Alternatives considered**: pandas (a heavy dependency for a few medians).

## R14. Tests without paid calls

- **Decision**:
  - `tests/conftest.py` blocks outgoing network connections for every test and sets dummy API
    keys, so a test that reached a provider would fail, not spend money (Principle VI, SC-001).
  - The scripted model is a `GenericFakeChatModel` subclass whose `bind_tools` returns a binding,
    driven by a function that picks the next message from the conversation so far (for example
    "replay the shortest solution", "answer in text", "keep moving into a wall", "use many
    tokens").
  - Runner tests use a test-only architecture written as a plain Python loop over `kit.model`
    and `kit.tool_node`, not a `StateGraph`, so no graph for the experimenter's A1 is written
    ahead of time.
  - A1 tests in `tests/arch/test_react.py` import `apl.arch.react` and skip while it does not
    exist, like the M1 boundary guard.
- **Rationale**: The runner is fully testable before A1 exists, and A1's graph stays the
  experimenter's work (Development Workflow).
- **Alternatives considered**: Recording real provider responses (costs money and goes stale).

## R15. Boundary check

- **Decision**: The M1 boundary test is extended. Files in `src/apl/arch/` may import from `apl`
  only `apl.kit`, `apl.dungeon.tools` and `apl.dungeon.results`. They may not import `openai`,
  `anthropic`, `langchain_openai`, `langchain_anthropic`, `langchain.chat_models` or
  `langchain_core.language_models`, and may not name `init_chat_model`, `ChatOpenAI` or
  `ChatAnthropic`. The existing `_episode` check stays. `AGENTS.md` gets the same rule.
- **Rationale**: Principle I requires architectures to use the runner's model, and Principle II
  keeps them away from runner internals (FR-010, SC-007).
- **Alternatives considered**: Checking only at run time (would catch a violation only on the
  path that runs).

## R16. Local model through Ollama (decided 2026-10-30, replaces R2's default)

- **Decision**: The default model is `ollama:qwen3:8b`, served by the local Ollama server
  (0.21.2, systemd service in WSL, `http://localhost:11434`), through LangChain's native
  `langchain-ollama` provider (1.1.0). The runner passes `num_ctx` (`APL_NUM_CTX`, default
  16,384) and the timeout (`client_kwargs={"timeout": APL_TIMEOUT_S}`). `num_ctx` is recorded in
  `run.json` and compared by the report, like the other run conditions. `APL_REASONING_EFFORT`
  maps to Ollama's `reasoning` (`none` turns thinking off). No API key is needed.
- **Rationale**:
  - The experimenter wants to run locally and free.
  - Ollama loaded `qwen3:8b` with a 4,096-token context. A long L3 episode needs about
    9–10K tokens (640 fixed plus about 110 per step, up to 78 steps), and Ollama cuts off the
    start of an over-long prompt silently, so the rules would be lost mid-episode.
  - The OpenAI-compatible endpoint (`/v1`) cannot set the context per request. The native
    provider can, which makes the context a recorded run condition instead of hidden server
    configuration.
  - Checked with one local call: a correct tool call (`move north`), usage reported
    (662 input, 246 output tokens), 16,384 context loaded in 7.4 GB of the 16 GB GPU, about 9 s
    from load.
- **Errors**: The Ollama client has no retries of its own, so the runner gives it an HTTP
  transport (`RetryTransport` in `run.py`) that retries 429, 5xx and connection errors up to
  `APL_MAX_RETRIES` times with growing pauses (FR-017). When those are used up, an
  `httpx.TransportError` counts as an infrastructure error (not scored); an Ollama
  `ResponseError` carries a `status_code` and is sorted like any provider error (R7, R8). A read
  timeout while a streamed answer is arriving is not retried.
- **SC-009**: plan.md's "small paid run" becomes a small `--execute` run on the configured model,
  free on the local one. The `--execute` gate stays (Principle VI).
- **Alternatives considered**: Ollama's OpenAI-compatible endpoint with `openai:qwen3:8b` and a
  base URL (no new dependency, but the context stays at the server default unless the systemd
  service is changed, which the runner cannot record); raising `OLLAMA_CONTEXT_LENGTH` in the
  service (needs sudo and is invisible in the results).
- **Output limit per call** (added after the first local run): `APL_MAX_OUTPUT_TOKENS`, default
  4,096, sent as `num_predict` to Ollama and `max_tokens` to other providers, recorded and
  compared. In the first local run, one `qwen3:8b` call in an L2 episode generated for over
  20 minutes. The token cap is only checked after a call returns, and the timeout applies per
  read, so neither stopped it. A normal call used about 250 output tokens.
