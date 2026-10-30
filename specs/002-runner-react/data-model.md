# Data Model: Runner, Results Format, Report and A1 ReAct

Types are frozen dataclasses unless marked mutable. File shapes are in
[contracts/results.md](contracts/results.md); the architecture interface is in
[contracts/kit.md](contracts/kit.md).

## Changes to M1 types (additive)

| Type | Change |
| --- | --- |
| `ErrorCode` | New member `unknown_tool` |
| `Tool` / `Action` | New pseudo-tool `unknown` with one argument (the attempted tool name). It appears only in logs |
| `Episode` | New method `unknown(name: str) -> ToolResult`: counts one step and one invalid action, returns `unknown_tool`, logs `Action("unknown", (name,))` |
| `frames.call` | Dispatches `unknown` to `Episode.unknown` |
| `render_text` step table | Shows the action as `unknown <name>` (from `str(Action)`, no code change expected) |

`AgentTools` is unchanged: still exactly `start`, `look`, `move`, `take`, `use`.

## Settings (`apl.runner.settings`)

The shared configuration (FR-001). Read once per run from the environment after loading `.env`
(research R11).

| Field | Env variable | Default | Rule |
| --- | --- | --- | --- |
| `model` | `APL_MODEL` | `ollama:qwen3:8b` | `provider:model` form |
| `temperature` | `APL_TEMPERATURE` | `None` (provider default) | float ≥ 0 when set |
| `reasoning_effort` | `APL_REASONING_EFFORT` | `None` (provider default) | non-empty string when set |
| `token_cap` | `APL_TOKEN_CAP` | `600_000` | int > 0 |
| `max_retries` | `APL_MAX_RETRIES` | `4` | int ≥ 0 |
| `timeout_s` | `APL_TIMEOUT_S` | `120` | number > 0 |
| `price_input`, `price_output` | `APL_PRICE_INPUT`, `APL_PRICE_OUTPUT` | `None` | USD per 1M tokens, ≥ 0; both or neither |
| `max_output_tokens` | `APL_MAX_OUTPUT_TOKENS` | `4096` | int > 0; Ollama `num_predict`, otherwise `max_tokens` (research R16) |
| `num_ctx` | `APL_NUM_CTX` | `16_384` | int > 0; sent to Ollama models only, recorded as `null` for others (research R16) |

An invalid value is an argument error (exit 2) naming the variable. `prompt_fingerprint` is a
derived property (research R11). `record()` returns the `settings` object of `run.json`.

## RunSpec (`apl.runner.spec`)

What `apl run` was asked to do (FR-012).

| Field | Type | Rule |
| --- | --- | --- |
| `architectures` | `tuple[str, ...]` | Registered and existing; no duplicates |
| `levels` | `tuple[str, ...]` | Each in `LEVELS`; no duplicates; `all` expands to L1, L2, L3 |
| `seed_set` | `"dev" \| "test"` | |
| `seeds` | `tuple[int, ...]` | From the set: all, the first `limit`, or `only` (each must be in the set) |
| `repeats` | `int` | ≥ 1 |

`episodes()` yields `EpisodeKey(arch, level, seed, repeat)` in the order of contracts/cli.md
(repeat numbers start at 1). `upper_bounds(settings)` returns model calls, tokens and optional cost
(research R10).

## Kit (`apl.kit`)

Built by the runner for one episode. Fields `model`, `tools`, `tool_node`, `base_prompt`, `start`,
`recursion_limit` as in contracts/kit.md. It holds the episode only inside `tool_node` (a closure
over `AgentTools` and the `Episode`), never as a public attribute.

`EpisodeEnded(Exception)`: raised by the meter and by `tool_node` once the episode has ended.

## Meter (mutable, `apl.runner.meter`)

The callback handler attached to the model for one episode (research R3). `raise_error = True`.

| Field | Type | Notes |
| --- | --- | --- |
| `episode` | `Episode` | To check whether it ended and to stop it at the cap |
| `token_cap` | `int` | |
| `llm_calls` | `int` | Started calls |
| `input_tokens`, `output_tokens` | `int` | Sums |
| `usage_missing` | `bool` | Set if any call returned no `usage_metadata` |
| `token_cap_hit` | `bool` | Set when the sum passes the cap; the episode is stopped at that moment |
| `output_limit_hits` | `int` | Calls whose answer was cut off by the output limit (`done_reason` or `finish_reason` is `"length"`) |
| `transcript` | `Transcript` | Messages and calls |

`on_chat_model_start`: if `episode.end_reason is not None`, raise `EpisodeEnded`; else count and
record the input. `on_llm_end`: record output, usage and latency; add tokens; if the total passes
the cap, set `token_cap_hit` and call `episode.stop()`.

## Transcript (mutable)

| Field | Type | Notes |
| --- | --- | --- |
| `messages` | `list[dict]` | Distinct messages in order of first appearance (keyed by their canonical JSON) |
| `calls` | `list[CallRecord]` | `input: list[int]`, `output: int`, `usage: dict \| None`, `latency_s: float` |

`to_dict()` gives the `*.conversation.json` shape.

## EpisodeRow (`apl.runner.results`)

One line of `episodes.jsonl` (FR-021). Fields and rules in contracts/results.md. Built by
`EpisodeRow.completed(key, run_id, seed_set, outcome, meter, latency, arch_error)` or
`EpisodeRow.failed(key, run_id, seed_set, dungeon, meter, latency, error)`.

**Derivations** (FR-022):
- `efficiency = round(optimal_steps / steps, 3)` if `success` else `None`;
- `token_cap_hit = meter.token_cap_hit`; `success`, `end_reason`, `steps`, `budget_hit` and
  `invalid_actions` come from the M1 outcome;
- `tool_calls = len(outcome.log)`; tokens are `None` when `meter.usage_missing`.

`EpisodeRow.parse(dict)` validates a row read back from disk (types, allowed values, required
fields) and raises `ValueError` with the line number on a mismatch.

## RunRecord (`run.json`)

| Field | Type | Notes |
| --- | --- | --- |
| `run_id` | `str` | `YYYYMMDD-HHMMSS-<arch>[+<arch>]`, with `-2`, `-3` on a clash |
| `started`, `ended` | ISO 8601 with offset; `ended` may be `null` | |
| `completed` | `bool` | `false` until every episode is done |
| `architectures`, `levels`, `seed_set`, `seeds`, `repeats` | from `RunSpec` | |
| `settings` | `Settings.record()` | |
| `code` | `{"commit": str \| null, "dirty": bool \| null}` | From `git rev-parse HEAD` and `git status --porcelain` |
| `versions` | `dict[str, str]` | Python and the installed LangGraph and LangChain packages |

**Run states**:

```text
created (completed: false, ended: null)
  ├─ every episode done ───────────────▶ completed (completed: true, ended set)
  ├─ permanent provider rejection ─────▶ stopped (completed: false, ended: null), exit 3
  └─ Ctrl-C ───────────────────────────▶ interrupted (completed: false, ended: null), exit 130
```

## Episode flow (runner, per `EpisodeKey`)

```text
generate(level, seed) → start_episode → Meter → model (with meter) → Kit → play(kit)
  play returns            → episode.stop() if not ended
  EpisodeEnded            → (episode already ended)
  provider error, retries exhausted, status not permanent → row status "error"
  provider error, permanent status                        → stop the run (exit 3)
  any other exception     → episode.stop(), arch_error recorded
→ write outcome.json (completed only), conversation.json (if any call), append row
```

## Report (`apl.runner.report`)

| Type | Fields |
| --- | --- |
| `LoadedRun` | `record: RunRecord`, `rows: list[EpisodeRow]`, `path` |
| `GroupStats` | per (arch, level): `episodes`, `success_rate`, `median_efficiency`, `invalid_per_episode`, `budget_hit_rate`, `token_cap_rate`, `median_calls`, `median_input_tokens`, `median_output_tokens`, `median_latency` |
| `Spread` | per (arch, level): `success_min`, `success_max`, `efficiency_min`, `efficiency_max` |

`check_compatible(runs)` raises `ValueError` naming every differing field among `seed_set`,
`model`, `temperature`, `reasoning_effort`, `token_cap`, `prompt_fingerprint` (FR-030, FR-031)
and returns notes for differing seed lists or repeats. `render(runs) -> str` produces the markdown
in contracts/results.md.

## Relationships

```text
Settings ─┐
RunSpec ──┴─▶ Run (run.json) 1──* EpisodeKey ──▶ Episode (M1) ─▶ Outcome (M1) ─▶ outcome.json
                                     │             ▲
                                     └─ Kit ─ play │ tool_node
                                        └─ model ─ Meter ─▶ Transcript ─▶ conversation.json
                                                     └──▶ EpisodeRow ─▶ episodes.jsonl
Run(s) ──▶ Report (report.md)
```
