# Contract: Run folder and report

```text
results/20261030-151200-react/
├── run.json                 # settings record
├── episodes.jsonl           # one row per finished episode
├── episodes/
│   ├── react-L1-1000-r1.outcome.json        # M1 outcome record (replayable)
│   ├── react-L1-1000-r1.conversation.json   # model calls
│   └── ...
└── report.md                # written by apl report
```

No file ever contains an API key.

## `run.json`

```json
{
  "run_id": "20261030-151200-react",
  "started": "2026-10-30T15:12:00+01:00",
  "ended": "2026-10-30T15:19:41+01:00",
  "completed": true,
  "architectures": ["react"],
  "levels": ["L1", "L2", "L3"],
  "seed_set": "dev",
  "seeds": [1000, 1001],
  "repeats": 1,
  "settings": {
    "model": "openai:gpt-6-luna",
    "temperature": "provider default",
    "reasoning_effort": "provider default",
    "token_cap": 600000,
    "max_retries": 4,
    "timeout_s": 120,
    "prompt_fingerprint": "a1b2c3d4e5f6"
  },
  "code": {"commit": "71c274a…", "dirty": false},
  "versions": {"python": "3.12.13", "langgraph": "1.2.18", "langchain": "1.4.7",
               "langchain-core": "1.7.3", "langchain-openai": "1.7.3"}
}
```

`temperature` and `reasoning_effort` are a number or string when set, otherwise
`"provider default"`. `code.commit` and `code.dirty` are `null` when git is not available.
`ended` is `null` while running or after a permanent provider error or an interruption.

## `episodes.jsonl` row

```json
{"run_id": "20261030-151200-react", "arch": "react", "level": "L2", "seed": 1001,
 "seed_set": "dev", "repeat": 1, "status": "completed", "success": true, "end_reason": "exit",
 "steps": 30, "optimal_steps": 12, "budget": 36, "efficiency": 0.4, "invalid_actions": 5,
 "budget_hit": false, "token_cap_hit": false, "llm_calls": 30, "tool_calls": 30,
 "input_tokens": 201311, "output_tokens": 11120, "latency_s": 41.2,
 "arch_error": null, "error": null}
```

| Field | Rule |
| --- | --- |
| `status` | `completed`, or `error` for an infrastructure error (research R7) |
| `efficiency` | `optimal_steps / steps` when `success`, else `null`; rounded to 3 decimals |
| `tool_calls` | Length of the episode log (every call, including uncounted `episode_over` calls) |
| `input_tokens`, `output_tokens` | Sums over model calls; `null` if any call reported no usage |
| `latency_s` | Wall time of the episode, rounded to 0.1 s |
| `arch_error` | Exception type and message when `play` raised a non-provider exception, else `null` |
| `error` | Provider error type and message for `status: "error"`, else `null` |

For `status: "error"`: `success`, `end_reason`, `steps`, `efficiency`, `invalid_actions`,
`budget_hit` and `token_cap_hit` are `null`; `optimal_steps` and `budget` are still filled.

## `*.outcome.json`

Exactly `Outcome.to_dict()` from specs/001-dungeon-environment/contracts/outcome.md. Not written
for `status: "error"` episodes (the episode did not finish).

## `*.conversation.json`

```json
{
  "messages": [
    {"type": "system", "content": "..."},
    {"type": "human", "content": "{\"ok\": true, ...}"},
    {"type": "ai", "content": "", "tool_calls": [{"name": "move", "args": {"direction": "east"}, "id": "call_1"}]},
    {"type": "tool", "content": "{\"ok\": true, ...}", "tool_call_id": "call_1", "name": "move"}
  ],
  "calls": [
    {"input": [0, 1], "output": 2, "usage": {"input_tokens": 812, "output_tokens": 64}, "latency_s": 1.4}
  ]
}
```

Each distinct message appears once in `messages` (LangChain's message dict form, `type` plus
`data` fields flattened). Each call lists its input as indices, its output index, the usage the
provider reported (`null` if none) and its latency (research R12). Written for every episode
that made at least one model call, including `error` episodes.

## Report

```markdown
# Report: react

> Development result (dev seeds). Must not be reported.

Runs: 20261030-151200-react · model openai:gpt-6-luna · temperature provider default ·
reasoning provider default · token cap 600,000 · prompt a1b2c3d4e5f6 · seeds dev 1000, 1001 ·
repeats 1

| Arch | Level | Episodes | Success | Efficiency (median) | Invalid / ep | Budget hit | Token cap hit | Calls (median) | Input tokens (median) | Output tokens (median) | Latency (median) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| react | L1 | 2 | 100% | 0.80 | 0.5 | 0% | 0% | 7 | 9,812 | 640 | 6.1s |

## Spread across repeats

| Arch | Level | Success (min–max) | Efficiency (min–max) |
| --- | --- | --- | --- |
| react | L1 | 83%–100% | 0.71–0.86 |

## Infrastructure errors (not scored)

| Arch | Level | Seed | Repeat | Error |
| --- | --- | --- | --- | --- |
| react | L3 | 1001 | 1 | RateLimitError: ... |

Notes: 1 episode has no token data. Run 20261030-151200-react is incomplete.
```

- Rows are sorted by architecture name, then level. The spread section appears only when some run
  has more than one repeat; the error section only when there are errors; notes only when needed.
- The header is `> Result on test seeds.` for test-seed runs.
- `Episodes` counts `completed` rows. Every rate and median is over `completed` rows; the
  efficiency median is over successful ones; token medians skip rows with `null` tokens. A median
  with no values is `—`.
- Combining runs: refused (exit 2) if `seed_set`, `model`, `temperature`, `reasoning_effort`,
  `token_cap` or `prompt_fingerprint` differ, naming each differing field. If the seed lists or
  repeats differ, the report adds a note naming them.
