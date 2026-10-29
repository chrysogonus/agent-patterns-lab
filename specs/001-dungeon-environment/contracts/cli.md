# Contract: `apl dungeon show`, text map and HTML picture

## Command

```text
apl dungeon show --level {L1,L2,L3} --seed N [--route solution|PATH] [--html OUT.html]
```

| Option | Meaning |
| --- | --- |
| `--level`, `--seed` | Which dungeon to show (required). An unknown level or a negative seed exits with code 2 and an error message |
| `--route solution` | Overlay the solver's shortest solution |
| `--route PATH` | Overlay a route file (format below) |
| `--html OUT.html` | Also write the picture: an animation with a route, a still image without one |

Output: the text map on stdout. Exit code 0 on success; 2 for invalid arguments or an invalid
route file.

## Route file

JSON. Either a plain list of actions:

```json
{"actions": [{"tool": "move", "args": ["east"]}, {"tool": "take", "args": ["red key"]}]}
```

or an outcome record from [outcome.md](outcome.md), whose `log` and `end_reason` are used. The
replayed results and end must match the logged ones, except that a `stopped` end is applied
after the replay, because stopping is not a tool call (research R7).

## Text map

Each room is a fixed-width cell, as wide as the longest label plus its markers. The walls are
`+`, `-` and `|`. A gap in a wall is an open door, and an uppercase color initial in a wall is a
locked door (`R`ed, `B`lue, `G`reen, `Y`ellow). Inside a cell are the label and its markers:
`S` start, `E` exit, a lowercase key initial (`r` = red key), and `*` for a room on the route.

```text
+------+------+------+
| k3S* | b7 * | a9   |
+--  --+------+--  --+
| m4 * R d2r* | p5   |
+------+--  --+--  --+
| x8   | h6  *  c2E* |
+------+------+------+
```

Notes on the example: the start is `k3`. The locked red door between `m4` and `d2` is shown as
`R`, the red key lies in `d2`, and the exit is `c2`. This is a sketch only. The tests check
content (every label, door, lock, key, start and exit appears), not exact spacing.

With a route, a step table follows the map:

```text
step  room  action              result
   0  k3    (start)
   1  m4    move south          ok
   2  m4    move east           locked (red)
   3  ...
visits: k3 0 | m4 1,2 | ...
end: c2 at step 9 (exit)
```

It shows every step's room, action and result, the events "took <key>" and "opened <color>",
failed actions with their error code, the visit numbers per room (all of them for revisited
rooms), and where the route ended (FR-025).

## HTML picture / animation

- A single file. No `http:`, `https:` or `//` references, no external `src` or `href`
  (FR-026).
- The SVG shows every room with its label, the doors, the locked doors in their color, the keys,
  the start and the exit.
- With a route: `<script type="application/json" id="apl-frames">` holds the frames
  (data-model `Frame`), followed by an inline player script and these controls:
  - play/pause (Space)
  - step back (←) and step forward (→)
  - a slider to jump to a step
  - a speed select (0.5×, 1×, 2×, 4×)
  - a panel with the step number, the action, the result and the inventory

  The player draws frame *i* only from `frames[i]` (FR-028).
- Without a route: no script, no controls.
- The same input always produces the same bytes (FR-026, SC-011).
