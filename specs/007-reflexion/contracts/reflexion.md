# Contract: A4 `reflexion`

Module `src/apl/arch/reflexion.py`, written by the agent at the experimenter's request (spec
FR-014). `play(kit: Kit) -> None`; imports only `apl.kit`, `apl.arch.*` and the problems'
public tools and results.

## Graph

Nodes `actor`, `act`, `reflector`, `restart`; transitions in [data-model.md](../data-model.md).
Invoked with `recursion_limit = kit.recursion_limit`.

## Prompts

| Job | System message | Human messages | Role |
| --- | --- | --- | --- |
| actor | base prompt, A2's map instructions for the problem, `ACTOR_INSTRUCTIONS` (with `kit.max_attempts`) | `Attempt n of m.`, then `Notes from earlier attempts:` with numbered notes (from attempt 2), then the start result on the attempt's first turn; the previous reply and its tool results; the map | `actor (attempt n)` |
| reflector | base prompt, `REFLECTOR_INSTRUCTIONS` | `Notes from earlier attempts:` (if any); `The attempt ended: <failure>.`; `Its last reply: <text>`; the map at the end of the attempt | `reflector` |

Texts per research R6. The reflector's reply text, stripped, is the note; an empty note is not
kept.

## Constants

`MAX_STALE = 12` actor turns in a row without a new room or cell. The attempt cap is
`kit.max_attempts`.

## Guarantees

- Only `act` calls `kit.tool_node`; reflector calls and restarts cost no step.
- `act` runs a reply's calls only up to its first `submit`: a submission ends the attempt either
  way, and later calls would run in a restarted world the attempt's map does not show.
- The map of each attempt starts from `kit.start` and holds only that attempt's tool results.
- Nothing shown to a model comes from outside tool results, the notes and A4's own counters.
- On the same level and seed, A4's base prompt, tool schemas and budget equal A2's.
