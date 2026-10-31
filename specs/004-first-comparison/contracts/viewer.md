# Contract: Viewer changes for M4

This adds to specs/003-viewer-mapstate/contracts/viewer-api.md. Everything not listed here is
unchanged. Research R4, R6.

## Events

| Event | New field | Value |
| --- | --- | --- |
| `thinking` | `role` | `"orchestrator"`, `"scout N"`, or `null` (single-agent architectures) |
| `turn` | `role` | as above |
| `step` | `scout` | the scout that made the call (0 for single-agent architectures) |

- Each model call keeps its own call number from `thinking` to `turn`, also when several calls run
  at the same time (matched by the call's run id).
- A `step` event's `call` is the latest call of the role `scout <scout>`. With no such role (all
  single-agent architectures), it is the latest call, as before.
- The "new input" of a `thinking` event is computed against the previous call of the same role.

## Frames

Frames (`start.frame`, `step.frame`, saved replays) get

```json
"scouts": [{"position": [0, 2], "inventory": ["red"]}, {"position": [1, 2], "inventory": []}]
```

when the episode has more than one scout. `position` and `inventory` stay scout 0's.

## Page

- One marker and one trail per scout, in four distinct colors defined as theme tokens; scout 0 keeps
  the current color. Each marker walks room by room as in the M3 fix.
- A model turn card is headed `Model call N · orchestrator` or `Model call N · scout K` when it has a
  role.
- "Agent's view" counts a room as seen when any scout has been in it.
- The slider, Play and saved replays show every scout's position at the chosen step.
- The architecture list shows `fanout`, `rounds` and `blackboard` once they are registered and
  written.
