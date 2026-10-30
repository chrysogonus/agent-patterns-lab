# Research: Browser Viewer and A2 Map State

Decisions for M3. Each one lists the choice, why it was made, and what else was considered:

- R1–R10 cover the viewer and the switch to vLLM;
- R11–R17 cover A2, carried over from the reviewed design in `docs/parked/m4-comparison/` with
  its review fixes.

M2's decisions (specs/002-runner-react/research.md) still hold unless one below replaces them.

## R1. A local web app without new dependencies

**Decision**: `apl serve` starts the standard library's `http.server.ThreadingHTTPServer`. It
binds to `127.0.0.1` only, on default port 8765 (`--port` changes it), and prints the URL. The
code is split in two:

- `apl.viewer.app` holds the request logic as plain functions that take parsed input and return
  `(status, content type, body)`;
- `apl.viewer.server` holds only the HTTP glue.

The page is one static file, `apl/viewer/assets/index.html`, with vanilla JavaScript and SVG and
no build step. The package data is shipped like M1's `player.html`.

**Rationale**:

- The viewer serves one local user and a handful of requests, plus one long event stream.
  A thread per request is plenty.
- Binding to loopback keeps it unreachable from the network (FR-001).
- Plain functions can be tested without sockets, which `tests/conftest.py` blocks.
- No framework, no `npm`, and nothing new in `pyproject.toml`.

**Alternatives considered**: FastAPI or Starlette with uvicorn, which are nicer for streaming but
add 3+ dependencies for 7 endpoints; a static HTML export per episode, which cannot show a live
run.

## R2. Live updates through Server-Sent Events

**Decision**: each episode is an `EpisodeSession`: a list of events, appended under a
`threading.Condition`. `GET /api/episodes/<id>/events` writes every event so far, then waits on
the condition for new ones, and ends after the `end` event. Each event is one SSE message
(`event: <type>`, `data: <json>`), and its `id` is its index. The event types:

| Event | When | Data |
| --- | --- | --- |
| `start` | The episode begins | arch, level, seed, model, settings record, budget, optimal steps, start frame |
| `thinking` | A model call starts | call number, the input messages after the prefix shared with the previous call's input |
| `turn` | A model call ends | call number, text, reasoning (if captured), tool calls, usage, latency |
| `step` | A tool call returns | step frame (`Frame.to_dict()`), action, result, index of the turn it belongs to |
| `stopping` | Stop was requested | — |
| `end` | The episode is over | the `EpisodeRow` as a dict (or an error without a row), and where it was saved |

**Rationale**: SSE is one-way, server to page, which is exactly the flow. Browsers reconnect by
themselves, and `EventSource` is built in. Sending the whole history to each new connection
covers reloads and second tabs (FR-014, SC-003) without a separate catch-up endpoint. An L3
episode has at most about 200 events, so this is cheap.

**Alternatives considered**: WebSockets, which are two-way and not available in the standard
library; polling, which is slower and adds load.

## R3. Observing an episode without touching the architectures

**Decision**: three small hooks. The architectures, the kit and `apl run` are unchanged.

1. `Episode` (`apl.dungeon.env`) gains `on_step: Callable[[LogEntry], None] | None = None`. It
   is called at the end of `_call()` for every logged call, including uncounted
   `episode_over` calls.
2. `frames._snapshot` becomes public as `frames.snapshot(episode, step, action, result)`, so a
   step event carries the same frame the M1 player draws.
3. `play_episode` (`apl.runner.episode`) gains two keyword arguments:
   - `callbacks`: extra LangChain callback handlers, passed to the model factory after the meter;
   - `on_episode`: called with the new `Episode` before the architecture starts. The viewer uses
     it to set `episode.on_step` and to keep the episode for Stop.

The viewer's `ViewerCallbacks(BaseCallbackHandler)`:

- emits `thinking` in `on_chat_model_start`, with the messages after the longest prefix it shares with the previous call's input (the whole input on the first call). Messages are
  compared by the same JSON key as `Transcript.add`:
  - for A1, the shared prefix is the whole earlier history, so only the previous reply and its
    tool results are new;
  - for A2, only the system message is shared, so its previous turn and its map are new on every
    turn, even when the map text is the same as before (after a failed move or a `look`).

  So A2's map appears every turn with no A2-specific code. Deduplicating against everything
  shown before would hide an unchanged map;
- emits `turn` in `on_llm_end`.

Its `raise_error` stays `False`, so a viewer bug can never end an episode. The meter keeps
`raise_error=True`.

**Rationale**: The model and the episode are the only two places where everything an
architecture does passes through. Hooking there shows the same thing for every architecture,
including later ones (FR-006). The model callbacks have to sit on the model object, not in
`with_config`, for the reason M2 R3 found: `bind_tools` drops `with_config` callbacks.

**Alternatives considered**: tailing the outcome log during the run, which is written only at
the end; wrapping `AgentTools`, which the kit builds inside `build_kit`.

## R4. One episode at a time, and stopping it

**Decision**: `app.start_episode(arch, level, seed)` returns 409 while a session is running.
Otherwise it starts a daemon thread that calls `play_episode` with the viewer's hooks and the
shared settings.

`POST /api/episodes/<id>/stop` calls `episode.stop()` and emits `stopping`. The meter's
`on_chat_model_start` then raises `EpisodeEnded` before the next call, and the tool node checks
before each call, so the episode ends after the current model turn (FR-012). A model call in
flight is not interrupted.

The session gets the `Episode` through `on_episode` (R3).

**Rationale**: a local GPU serves one request at a time well (FR-013). Stopping by ending the
episode reuses the M2 guard and needs no new cancellation path. `Episode.stop()` only sets a
field, which is safe across threads in CPython.

## R5. Saving and replaying episodes

**Decision**: when a session ends, its folder is
`results/viewer/<YYYYMMDD-HHMMSS>-<arch>-<level>-<seed>/`, holding:

- `events.jsonl`: the events, one per line, written as they happen. A crash then still leaves
  the episode up to that point.
- `outcome.json` and `conversation.json`: the M2 formats, so
  `apl dungeon show --route …/outcome.json` keeps working (US4/AC3).
- `episode.json`: the `EpisodeRow`, the settings record, the code version and the package
  versions.

`GET /api/episodes` lists the folders, newest first, from their `episode.json`.
`GET /api/episodes/<id>/events` for a saved episode streams its `events.jsonl` and ends. The page
then uses the same code for live and replay (FR-019, SC-004). `results/` is gitignored.

**Rationale**: replay from the event log reproduces exactly what was shown live, including the
model turns, which the outcome file does not hold. The M2 files keep the existing tools working.

**Alternatives considered**: rebuilding replays from `outcome.json` and `conversation.json`. It
needs mapping steps to turns again, and a stopped episode's "stopping" moment would be lost.

## R6. Dungeon endpoint and seeds

**Decision**: `GET /api/dungeon?level=L2&seed=1234` returns:

- `svg`: the existing drawing, `render_html.svg(layout, animated=True)` (was `_svg`), which now also draws one
  `<rect class="room" id="room-x-y">` per room above the drawing and below the agent, for the agent's view. The
  existing HTML output gets the same rects; its tests check walls, keys and labels, which stay
  unchanged.
- `cell` and `margin`, as the M1 player uses them.
- `budget`, `optimal_steps`, `start`, `exit` and `size`.
- `solution`: the frames from `build_frames(dungeon, dungeon.solution.actions)`.

The seed rules are:

- **Test seeds** (`TEST_SEEDS`, 2000–2019) get 403, with the message "test seeds are reserved
  for reported results (Constitution V)". The same check applies when starting an episode.
- **Seeds that are not whole numbers ≥ 0** get 400, with `generate`'s message.
- **Random seeds** are drawn on the page from 0–999,999, skipping the test seeds.
- **Dev seeds** come from `GET /api/options` and are offered as quick picks.

**Rationale**: everything the page draws comes from the M1 renderer and frames, so the viewer and
`apl dungeon show --html` cannot disagree. `generate` is deterministic, so the same level and
seed always draw the same dungeon (FR-002).

## R7. The page

**Decision**: `index.html` keeps all its state in one object and redraws from it, as the M1
player's `render(n)` does.

- **Controls:**
  - level select, seed input, "random" button, dev-seed quick picks, Generate;
  - architecture select (from `/api/options`), Run, Stop;
  - a "saved episodes" select.
- **Map:**
  - the agent dot and trail, failure flash, taken keys and opened doors, as in `player.html`;
  - "agent's view": rooms whose position never appeared in a frame up to the shown step get the
    class `fog`;
  - "shortest solution": a dashed polyline through the solution frames' room centers.
- **Step control:**
  - a slider over all steps so far, plus a "follow live" toggle that turns off when the user
    scrubs (FR-015);
  - Play/Pause and speed for replays.
- **Side panel:**
  - one card per model turn;
  - a "waiting for the model (n s)" line during `thinking`, timed on the page;
  - collapsible new input (A2's map shows up here) and reasoning, the text, and each tool call
    with its result;
  - the step cards link to the map step.
- **Stats bar:** steps/budget, optimal, model calls, tokens, elapsed time, and at the end the end
  reason and efficiency.

All text from the model is inserted with `textContent`, never as HTML.

**Rationale**: one file is easy to ship, read and change. Redrawing from state makes live,
scrubbing and replay the same code path. Using `textContent` keeps model output from injecting
markup.

## R8. Which models may run from the page (Constitution VI)

**Decision**: running is allowed without further permission when the model's provider is local:
`ollama:` or `vllm:`. For any other provider, `apl serve` must be started with `--execute`.
Otherwise `/api/options` reports `can_run: false`, Run is disabled with an explanation, and
`POST /api/episodes` returns 403 (SC-005). Browsing and replay always work.

**Rationale**: a local model costs nothing. The constitution's rule exists for paid calls, and
the permission flag keeps it for every other provider.

## R9. vLLM as the local model (replaces M2 R16's default)

The experimenter now serves `RedHatAI/Qwen3.5-9B-quantized.w4a16` with vLLM. Probed
2026-10-30, the server:

- listens on `http://localhost:8001/v1` with served name `qwen3.5-9b`;
- runs with `--max-model-len 8192`, `--reasoning-parser qwen3` and
  `--enable-auto-tool-choice --tool-call-parser qwen3_coder`;
- answers with the lab's base prompt and tools with a correct tool call in **1.6–2.4 s**, where
  Ollama `qwen3:8b` took about 9 s. That used 892 prompt tokens and 119–163 completion tokens, of
  which 91–135 were reasoning;
- returns the reasoning in `message.reasoning`, separate from the content.

**Decision**:

- **Model string:** `vllm:<served name>`, with the new setting `APL_BASE_URL` (default
  `http://localhost:8001/v1`). The new default is `APL_MODEL=vllm:qwen3.5-9b`. `ollama:` and
  `openai:` stay supported.
- **Model class:** `default_model_factory` builds `VLLMChat`, a small subclass of `ChatOpenAI` in
  `apl.runner.vllm`, with `base_url`, `api_key="EMPTY"`, `max_tokens`, `timeout`, `max_retries`
  and `temperature` (if set). It overrides `_create_chat_result` to copy
  `message.reasoning`, or the older `reasoning_content`, into
  `additional_kwargs["reasoning_content"]`.
- **Reasoning:** `ChatOpenAI` does not send `additional_kwargs["reasoning_content"]` back to the
  server (checked in `_convert_message_to_dict`, langchain-openai 1.7.3). So capturing it is for
  display and the transcript only, and it **does not change what any architecture sends**. The
  thinking-capture question for Ollama does not arise on vLLM.
- **Context:** vLLM's context is set on the server. At the start of a run, and when `apl serve`
  starts, the runner reads `max_model_len` from `GET {base_url}/models` and records it as
  `num_ctx` in the settings record. That is a metadata request, not a model call, and it happens
  only with `--execute` or in `apl serve`. The dry run shows `context: from the server`.
- **Output tokens:** with an 8,192-token context, the M2 default of 4,096 output tokens would
  leave only 4,096 for the prompt. For `vllm:` the default `max_output_tokens` becomes 1,024,
  which is about 6× the observed completions, and `APL_MAX_OUTPUT_TOKENS` still overrides it.
- **Key and prices:** `required_key_var("vllm:…")` is `None`. Prices stay 0.

**Rationale**: vLLM is 4× faster per call, which makes live watching pleasant: an L1 episode
takes about 20 s instead of 1 minute. The `ChatOpenAI` subclass adds about 15 lines, against the
alternatives:

- a new `langchain-vllm` style dependency;
- `openai:` with a base URL. It would share `OPENAI_API_KEY`, which holds a real paid key in this
  `.env`, so a mistyped URL could send requests to the paid API.

**Alternatives considered**: keeping Ollama as the default (slower, and the experimenter has
switched); `init_chat_model("openai:…", base_url=…)` (it loses the reasoning).

## R10. A prompt that outgrows the context is the architecture's failure

**Decision**: a provider error that says the prompt does not fit the context is now classified
as an **architecture failure**: the episode ends `stopped`, with
`arch_error = "context window exceeded: …"`, and it is scored. It used to be a permanent
provider error that stopped the whole run with exit code 3. The detection covers:

- vLLM: status 400 with "maximum context length" in the message (probed);
- OpenAI: the error code `context_length_exceeded`.

Every other 400/401/403/404/422 stays permanent.

**Rationale**: A1's history grows with every turn. At 8,192 tokens, a long L3 episode will
outgrow it, and that is A1's weakness, which is exactly what A2 addresses. Stopping a whole run,
or showing it as an infrastructure error in the viewer, would hide a real result. Ollama
truncates silently instead (M2 R16), and that stays a documented limitation.

**Alternatives considered**: trimming A1's history in the kit, which would change A1 and the
shared setup.

## R11. A2's graph and state

**Decision**: A2 is a `StateGraph` with two keys and two nodes:

- `messages` holds **only the latest turn**: the model's last reply, then that reply's tool
  results. It has no reducer, so each write replaces it.
- `map` holds the `DungeonMap` ([data-model.md](data-model.md)).
- `agent` builds the model input from the map and `messages` (R12), calls `kit.model` with the
  tools bound, and returns `{"messages": [reply]}`.
- `act` calls `kit.tool_node(state)`, applies each tool call and its result to the map in order
  (R13), and returns `{"messages": [reply, *results], "map": map}`.
- The route is the same as A1's: after `agent`, go to `act` if the reply has `tool_calls` or
  `invalid_tool_calls`, else end. After `act`, go back to `agent`.
- It is invoked with `config={"recursion_limit": kit.recursion_limit}`, as A1 is.

**Rationale**: Without a reducer, the history never builds up in the state. FR-023 then holds
by construction rather than by trimming the history. Updating the map in the same node that runs
the tools keeps each call next to its result, so the map never sees a result without its call.

**Alternatives considered**:

- A1's `MessagesState` with the history trimmed before each model call. The history would still
  sit in the state, and the trimming is one more place to get wrong.
- A separate `update_map` node after `tools`. That adds an edge and a node for no gain.
- LangGraph's `ToolNode`. Rejected in M2 R4: it runs calls in parallel and skips step counting.

## R12. What the model sees each turn

**Decision**: Each call sends these messages, in this order:

1. `SystemMessage(kit.base_prompt + "\n\n" + MAP_INSTRUCTIONS)`.
2. On the first turn, `HumanMessage(kit.start)`, as in A1. On later turns, the previous reply
   (`AIMessage` with its tool calls) and its `ToolMessage`s.
3. `HumanMessage(rendered map)`. It comes last, so the model reads the current state just before
   it answers.

**Rationale**: This is FR-023 exactly. The model sees the result of what it just did, so it can
read an error message, and everything older reaches it only through the map. Both providers
accept a user message after tool results. OpenAI requires each `ToolMessage` to follow its
`AIMessage`, and it does. The first observation is the same message A1 gets.

**Alternatives considered**:

- The map before the previous turn. Then the newest information would sit in the middle of the
  prompt.
- No previous turn at all, only the map. The model would lose the error text of a failed call,
  and an error such as `wrong_key` is not in the map.

## R13. How the map is updated from tool results

**Decision**: `DungeonMap.apply(name, args, result)` takes one tool call (name and arguments
from the `AIMessage`) and its parsed result (the `ToolMessage` JSON, M1 format). It works only
from those values:

| Result | Map change |
| --- | --- |
| `move` with `ok`, `data` a room | Record that the current room's exit in `direction` leads to `data.label`. Record that the new room's opposite exit leads back. Then record the room (below) and make it the current room |
| `look` with `ok` | Record the room (below) |
| Record a room | Store its exits (direction → lock color or none) and items as shown now, and set the inventory from `data.inventory` |
| `take` with `ok` | Set the inventory. Remove the newly held item from the current room's items |
| `use` with `ok` (`DoorOpened`) | Clear the lock on that exit of the current room and add it to the opened doors. If the exit's destination is known, clear the opposite exit's lock there too |
| Any result with `ok: false` | No change |

The start description (`kit.start`) seeds the map as the first recorded room.

The results of the batch that ends the episode are not applied. `kit.tool_node` raises
`EpisodeEnded` as soon as a call reaches the exit or the budget, without returning the replies
of that batch. After that, no model call can happen (the meter refuses it), so nobody could ever
see that last map update. This needs no change to the kit. "After every step" in FR-020 and
SC-007 is checked for every step before the one that ends the episode, and the tests include a
batch that ends at the exit and one that ends at the budget, to show they end cleanly.

The map stores no step count and no budget. Rooms are identified by label: labels are unique
per dungeon (M1).

Failed results change nothing because the map already holds what they could reveal:

- `no_door` and `invalid_direction` concern exits that the room view already listed or left out;
- `locked` repeats a color the room view already showed.

The spec's edge case ("records nothing new except, where the error reveals it, …") therefore
amounts to no change.

**Rationale**: Every entry follows from a result A2 received. Constitution II is satisfied, and
so is the plain-code-node clause. The reverse connection comes from the base prompt's rule that
rooms are connected by doors: a door between two rooms works both ways. A2 does not peek to learn
it (US3/AC3).

**Alternatives considered**:

- Recording failed moves as "tried". With full room views, that information is redundant.
- Reading the `ToolResult` objects instead of the JSON. A2 sees the same JSON the model sees, so
  the map cannot know more than the conversation shows.

## R14. Rendering the map

**Decision**: `DungeonMap.render()` produces plain text in a fixed order: rooms in the order they
were first seen, and exits in the order north, east, south, west. Example:

```text
Your map (built from your tool results so far):
You are in: c3. Inventory: red key.
Rooms seen:
- c3 (you are here): north -> e9; east: unexplored; south: unexplored, locked (blue)
- e9: south -> c3; west: unexplored; items: green key
Doors you opened: c3 east (red).
Unexplored exits: c3 east; c3 south (locked, blue); e9 west.
```

The exit is not listed: reaching it ends the episode. The text holds only labels, directions,
colors and item names, never step counts.

**Size check (SC-008)**: an L3 dungeon has 25 rooms, and labels are short, like `c3`. All room
lines of a fully known L3 dev dungeon come to 795–807 characters (measured on the 10 seeds), so
the whole render stays under about 1,500 characters. The map is ASCII text, and every token
covers at least one character, so its character count is a guaranteed upper bound on its token
count, whatever the tokenizer. The test explores each L3 dev dungeon completely and requires the
render to be at most `num_ctx / 4` characters: 2,048 for vLLM's 8,192-token context. The real
runs confirm it: the meter records the input tokens of every A2 call in the conversation files.

**Rationale**: A deterministic order makes the render testable and keeps the prompt stable from
turn to turn, which helps a small model. The explicit "Unexplored exits" line is part of the map
named in FR-020 ("exits not yet tried"), not advice.

**Alternatives considered**: a JSON map, which costs more tokens and is harder for an 8B model to
read; an ASCII grid, which would require coordinates that the agent does not know (labels are not
coordinates).

## R15. A2's own instructions

**Decision**: `MAP_INSTRUCTIONS` only explains the map: that it is built from the agent's tool
results, that it replaces the conversation history, what "unexplored" and "locked (color)" mean,
and that the latest tool results appear just before it. It gives no strategy, such as "go to the
nearest unexplored exit" or "pick up every key".

**Rationale**: A2 tests plan.md's question "does explicit memory beat history?". Strategy advice that A1
lacks would mix a prompt effect into the memory effect. Node instructions on top of the base
prompt are allowed (Constitution III). The base prompt and the tool schemas, and so the
fingerprint, stay as in M2.

**Alternatives considered**: a stronger exploration prompt, which belongs to a later architecture
or a separate prompt experiment.

## R16. Where the A2 code lives

**Decision**: two modules in `src/apl/arch/`:

- `dungeon_map.py` holds `DungeonMap`: building it from the start description, applying results,
  and rendering. It has no LangGraph imports.
- `mapstate.py` holds `play(kit)`, the graph and `MAP_INSTRUCTIONS`.

The registry gains `"mapstate": "apl.arch.mapstate"`. I (the agent) write both modules, as
the experimenter asked (spec Assumptions).

**Rationale**: plan.md has A3 and A6 build on the map, so it gets its own module. The module can
be tested without a model. Both stay inside the import boundary: `apl.arch` may import
`apl.arch`.

## R17. Testing A2 without a model

**Decision**:

- `replay_solution` in `tests/runner/scripted.py` now counts its own calls instead of counting
  `ToolMessage`s in its input. A2 does not send the history, so the old counting would replay
  step 1 forever. A1's tests are unaffected: one call still uses `per_turn` actions.
- SC-007 needs an independent check, an oracle. A test helper derives the expected map after
  each step from the layout and the M1 frames (`build_frames`):
  - the visited positions and their labels;
  - for each visited room, its doors and items as they are now, except that a door opened from
    the other side shows as still locked until a move through it makes the connection known;
  - the edges walked, in both directions;
  - the inventory.

  Tests may read the layout; architectures may not.
- The scripted routes cover a failed move, a `locked` move, a `take`, a `use`, a revisit, and
  several calls in one turn, on the `tests/dungeon/reference.py` layouts and on dev dungeons.

**Alternatives considered**: comparing the render against hand-written strings only. That covers
too few cases for "100% of steps" (SC-007). Hand-written strings stay as format checks (US3/AC3,
AC4).
