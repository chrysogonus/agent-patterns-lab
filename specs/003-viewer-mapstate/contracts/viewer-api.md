# Contract: Viewer HTTP API and events

Served by `apl serve` on `http://127.0.0.1:<port>/` (research R1). All JSON is UTF-8. Errors
are returned as `{"error": "<message>"}` with the status shown.

## `GET /`

Returns the page (`text/html`), which is `apl/viewer/assets/index.html` unchanged.

## `GET /api/options`

```json
{
  "levels": ["L1", "L2", "L3"],
  "dev_seeds": [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009],
  "test_seeds": [2000, 2019],
  "architectures": ["mapstate", "react"],
  "model": "vllm:qwen3.5-9b",
  "settings": {"model": "vllm:qwen3.5-9b", "temperature": "provider default", "num_ctx": 8192, "...": "..."},
  "can_run": true,
  "cannot_run_reason": null,
  "models": [
    {"name": "vllm:qwen3.5-9b", "cannot_run_reason": null},
    {"name": "openai:gpt-6-luna", "cannot_run_reason": "openai:gpt-6-luna is a paid provider; ..."}
  ]
}
```

- `test_seeds` is the inclusive range `[first, last]`.
- `architectures` lists the registered architectures whose module exists, sorted.
- `can_run` is `false` for a provider that is not local without `--execute` (research R8). In
  that case `cannot_run_reason` says so. Both fields are about the default model (`APL_MODEL`).
- `models` is the page's model switch (added 2026-10-31): the default model first, then the
  others in `apl.viewer.app.MODELS`, each with the same `.env` settings and its own
  `cannot_run_reason`.
- `problems.<name>.about` (added 2026-11-02) maps each listed architecture to its About card on
  that problem, from `apl.viewer.about.about(arch, problem)`: `summary`, the drawing (`width`,
  `height`, `nodes` with `id`, `label`, `kind` (`model`, `code`, `end`), box, `roles` and
  `group`; `edges` with `source`, `target`, `label`, `bend`; `groups` for subgraphs) and `facts`,
  a list of `[label, text]` rows (Model sees, Memory, Tools, Ends when, and the architecture's
  own rows). Node ids are the compiled graph's node names (`<group>/<name>` inside a subgraph);
  `tests/viewer/test_about.py` checks them against the graphs. Architectures without a card,
  such as test doubles, are left out.

The page shows the card for the selected agent, or for the episode being watched, above the
model turns. During an episode the model node whose `roles` holds the first word of the current
call's role (`""` for a call without one) is lit: on each `thinking` event, and on the slider
through the `call` of the step shown.

## `GET /api/dungeon?level=<L>&seed=<n>`

| Status | When |
| --- | --- |
| 200 | `{"level", "seed", "size", "budget", "optimal_steps", "start", "exit", "cell", "margin", "svg", "solution"}`. `solution` is a list of `Frame.to_dict()`, starting with step 0 |
| 400 | Unknown level, or a seed that is not a whole number ≥ 0 |
| 403 | A test seed: `"seed 2003 is a test seed; test seeds are reserved for reported results"` |

The same level and seed give byte-identical responses (FR-002).

## `POST /api/episodes`

The request body is `{"arch": "react", "level": "L1", "seed": 1000, "model": "vllm:qwen3.5-9b"}`.
`model` is optional (default: `APL_MODEL`) and must be one of `models`.

| Status | When |
| --- | --- |
| 201 | `{"id": "<episode id>"}`. The episode runs in the background |
| 400 | Unknown level, architecture or model, an unwritten architecture, or a bad seed |
| 403 | A test seed, or the chosen model's `cannot_run_reason` is set |
| 409 | Another episode is running: `{"error": "...", "running": "<id>"}` |

The id is the saved folder name (`<YYYYMMDD-HHMMSS>-<arch>-<level>-<seed>`).

## `POST /api/episodes/<id>/stop`

| Status | When |
| --- | --- |
| 202 | Stop requested. A `stopping` event follows, and `end` comes after the current model turn |
| 404 | No such running episode |

Stopping an episode that is already stopping is still 202.

## `GET /api/episodes`

Returns the saved episodes, newest first. The running one is listed first with `"running": true`.

```json
[{"id": "20261030-201500-mapstate-L2-1003", "arch": "mapstate", "level": "L2", "seed": 1003,
  "end_reason": "exit", "steps": 14, "optimal_steps": 9, "started": "2026-10-30T20:15:00+01:00",
  "running": false}]
```

## `GET /api/episodes/<id>/events`

Returns `text/event-stream`. Every event so far is sent first. For a running episode, new events
follow as they happen, and the stream closes after `end`. For a saved episode, the stream closes
after its last event. 404 for an unknown id.

Each event is sent as:

```text
id: <index>
event: <type>
data: <json>

```

| Type | Data |
| --- | --- |
| `start` | `{"arch", "level", "seed", "model", "settings", "budget", "optimal_steps", "frame", "started"}`. `frame` is the step-0 `Frame.to_dict()`; `started` is an ISO time |
| `thinking` | `{"call": n, "new_input": [{"type": "system"\|"human"\|"ai"\|"tool", "content": str}, ...]}`. `new_input` is the input messages after the longest prefix shared with the previous call's input (all of them on the first call), in order. A message repeated later, such as an unchanged A2 map, is included again |
| `turn` | `{"call": n, "text": str, "reasoning": str\|null, "tool_calls": [{"name", "args"}], "invalid_tool_calls": [...], "usage": {"input_tokens", "output_tokens"}\|null, "latency_s": float, "output_limit_hit": bool}` |
| `step` | `{"index", "step": int\|null, "call": n, "action": {...}, "result": {...}, "frame": {...}}`. `step` is `null` for an uncounted `episode_over` call; `call` is the turn that made the tool call |
| `stopping` | `{}` |
| `end` | `{"row": EpisodeRow dict \| null, "error": str \| null, "saved": "<folder>"}`. `row` is `null` (with `error`) only when the provider rejected the request permanently or the viewer itself failed |

Ordering guarantees:

- `start` comes first and `end` last.
- Each `turn` follows its `thinking`.
- A turn's `step` events follow its `turn`, in the order of the tool calls.
- No `step` follows `end`.

## Security

- The server listens only on `127.0.0.1`.
- Episode ids and folder names are matched against `^[0-9]{8}-[0-9]{6}-[a-z0-9_]+-L[1-3]-[0-9]+$`
  before any file is touched. This blocks path traversal.
- The page inserts all model and tool text with `textContent`.
