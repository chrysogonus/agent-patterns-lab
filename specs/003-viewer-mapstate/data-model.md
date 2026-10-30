# Data Model: Browser Viewer and A2 Map State

M2's types (specs/002-runner-react/data-model.md) are unchanged unless listed here.

## Hooks on existing types

| Type | Change | Research |
| --- | --- | --- |
| `Episode` (`apl.dungeon.env`) | New attribute `on_step: Callable[[LogEntry], None] \| None = None`, called after every log append in `_call()` | R3 |
| `frames.snapshot(episode, step, action, result) -> Frame` | Public name for `_snapshot`. The old name is removed and its callers are updated | R3 |
| `play_episode(...)` (`apl.runner.episode`) | New keyword arguments `callbacks: Sequence[BaseCallbackHandler] = ()` and `on_episode: Callable[[Episode], None] \| None = None` | R3 |
| `Settings` (`apl.runner.settings`) | Default `model = "vllm:qwen3.5-9b"`; new `base_url = "http://localhost:8001/v1"`; `max_output_tokens = 1024`; `load_settings` uses 4,096 instead for other providers when `APL_MAX_OUTPUT_TOKENS` is unset | R9 |
| `Settings.record()` | Adds `base_url` (`vllm:` only, otherwise `null`). `num_ctx` is recorded for `ollama:` and `vllm:`. For `vllm:`, `apl.runner.vllm.with_server_context(settings)` puts the server's `max_model_len` into `num_ctx` before a run or viewer episode (it raises `ValueError` if the server cannot be reached) | R9 |
| `svg(layout, animated)` (`apl.dungeon.render_html`, was `_svg`) | Adds `<rect class="room" id="room-{x}-{y}">` per room, drawn above the dungeon and below the agent and trail, so the fog dims labels and keys but never the agent | R6 |
| Error classification in `play_episode` | Context overflow → `arch_error` "context window exceeded: …" | R10 |

## EpisodeSession (`apl.viewer.events`)

One live or saved episode in the viewer.

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | `str` | The folder name `<YYYYMMDD-HHMMSS>-<arch>-<level>-<seed>` |
| `folder` | `Path` | `results/viewer/<id>/` |
| `events` | `list[dict]` | `{"type", "data"}`, in order. Only appended, never changed |
| `done` | `bool` | Set after `end` |
| `episode` | `Episode \| None` | Set through `on_episode`. Used by Stop |
| `condition` | `threading.Condition` | Notified on every append and when done |

Operations:

- `emit(type, data)` appends an event, writes it as one line to `events.jsonl`, and notifies.
- `stream(from_index)` yields events from that index and blocks for new ones until `done`.
- `load(folder)` builds a done session from `events.jsonl` for replay.

**Invariants**: the event order of contracts/viewer-api.md; `done` exactly when the last event is
`end`; `events.jsonl` holds exactly `events`.

## Viewer (`apl.viewer.app`)

| Field | Meaning |
| --- | --- |
| `settings` | Loaded once at start |
| `context` | `num_ctx` for the record (the server's value for `vllm:`) |
| `can_run` | Research R8 |
| `results_dir` | `results/viewer/` |
| `running` | The running `EpisodeSession`, or `None`; set and cleared under a lock |
| `model_factory`, `architectures` | Injected; tests pass the scripted model and test architectures |

## ViewerCallbacks (`apl.viewer.events`)

A `BaseCallbackHandler` with `raise_error = False`.

- It keeps the keys (as in `Transcript.add`) of the previous call's input. `new_input` is the part after the longest shared prefix.
- `on_chat_model_start` emits `thinking` with the unseen input messages.
- `on_llm_end` emits `turn`. Its `reasoning` is `additional_kwargs.get("reasoning_content")`.

## Saved episode folder (`results/viewer/<id>/`)

| File | Content |
| --- | --- |
| `events.jsonl` | One event per line, `{"type", "data"}` |
| `outcome.json` | M1 outcome record (absent for an infrastructure error, as in M2) |
| `conversation.json` | M2 transcript (absent if no model call was made) |
| `episode.json` | `{"row": EpisodeRow, "settings": record, "code": {...}, "versions": {...}, "started", "ended"}` |

## DungeonMap (`apl.arch.dungeon_map`)

A2's explicit memory. It is built only from tool results (research R13). It is mutable: `act`
updates it in place and returns it as the new state value.

| Field | Type | Meaning |
| --- | --- | --- |
| `rooms` | `dict[str, RoomNote]` | Rooms seen, by label, in the order first seen |
| `current` | `str` | Label of the room the agent is in |
| `inventory` | `tuple[str, ...]` | Item names, as the last room or inventory view showed them |
| `opened` | `list[tuple[str, str, str]]` | (room label, direction, color) of every door opened with `use`, in order. The color comes from the `DoorOpened` result, because the exit's lock is cleared |

### RoomNote

| Field | Type | Meaning |
| --- | --- | --- |
| `exits` | `dict[str, str \| None]` | Direction → lock color as last seen (`None`: no lock), in north, east, south, west order |
| `leads_to` | `dict[str, str]` | Direction → label of the room behind it, once known |
| `items` | `list[str]` | Items in the room as last seen, minus the ones taken since |

**Operations**:

- `DungeonMap.from_start(start_json: str)` builds the map with one room, which is the current
  room.
- `apply(name: str, args: Mapping, result: Mapping)` applies one tool call with its parsed result
  (research R13). Results with `ok: false` change nothing.
- `render() -> str` returns the text of research R14 and contracts/mapstate.md.

**Invariants**:

- `current` is in `rooms`.
- Every `leads_to` target is in `rooms`.
- If `rooms[a].leads_to[d] == b`, then `rooms[b].leads_to[opposite(d)] == a`.
- An exit in `opened` has lock `None`.
- No field holds a position, a step count or a budget.

## MapState (A2 graph state, `apl.arch.mapstate`)

| Key | Type | Reducer | Meaning |
| --- | --- | --- | --- |
| `messages` | `list[BaseMessage]` | none (replaced on each write) | The latest turn only: `[AIMessage]` after `agent`, `[AIMessage, ToolMessage...]` after `act`, `[]` at the start |
| `map` | `DungeonMap` | none | The map |

The model input per turn:

```text
[System(base_prompt + MAP_INSTRUCTIONS), Human(start) | *messages, Human(map.render())]
```

The first turn uses `Human(start)`; later turns use `*messages`.
