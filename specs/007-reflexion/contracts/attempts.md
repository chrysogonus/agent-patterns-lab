# Contract: Attempts in the problems, the kit and the runner

## Episode API (`apl.dungeon.env.Episode`, `apl.survey.env.Episode`)

- `MAX_ATTEMPTS = 3` in each env module.
- `attempt: int`, `max_attempts: int = 1`, `on_restart: Callable[[], None] | None = None`.
- `restart() -> bool` per [data-model.md](../data-model.md). Never counts a step, never writes a
  log entry.
- Survey `submit` per the data-model's submit-result table.
- With `max_attempts == 1`, every method behaves exactly as before specs/007.

## Kit (`apl.kit.Kit`)

- `restart: Callable[[], bool]` (default: always False), `max_attempts: int` (default 1).
- `build_kit` for both problems sets both from the episode; `restart` takes the kit's lock.
- `kit.start` stays the start result; after a restart the world looks exactly like it.

## Registry and runner

- `registry.RETRYING = frozenset({"reflexion"})`; `ARCHITECTURES["reflexion"] =
  "apl.arch.reflexion"`; `SUPPORTS["reflexion"]` both problems.
- `play_episode` sets `episode.max_attempts = MAX_ATTEMPTS` for retrying architectures before the
  kit is built.
- `EpisodeRow.attempts` per the data model.
- `meter.LEAD_ROLES` gains `"reflector"`; `compare.REFERENCES["reflexion"] = "mapstate"`.

## Report

A section `## Attempts`, only when some completed row has `attempts > 1`:

```text
## Attempts

| Arch | Level | Attempts (median) | Attempts (max) |
| --- | --- | --- | --- |
| reflexion | L1 | 1 | 2 |
```

Rows without `attempts` count as 1. No other report text changes.

## Replay (`apl.dungeon.frames`)

- `build_frames(..., attempts: Sequence[int] | None = None, final_attempt: int = 1)`: before an
  action whose attempt is higher than the replay's, the replay restarts; after the last action it
  restarts up to `final_attempt`.
- `RouteFile.attempts` from the log entries' `attempt` (default 1) and the outcome's `attempts`.

## Viewer

- Event `restart`: `{"attempt": n, "frame": <frame after the restart>}`, emitted from
  `episode.on_restart`; saved and replayed with the other events.
- Frames carry `"attempt": n` when n > 1.
- The page: a card "Attempt n starts"; trail and fog from the current attempt's frames; earlier
  attempts as `#trail-past` (dashed, faded); "Attempt n / max" in the stats.
