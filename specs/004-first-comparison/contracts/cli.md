# Contract: CLI changes for M4

This adds to specs/002-runner-react/contracts/cli.md and specs/003-viewer-mapstate/contracts/cli.md.
Everything not listed here is unchanged. Research R10–R13, R16; based on the parked
`docs/parked/m4-comparison/contracts/cli.md`.

## `apl run`

- `--arch` accepts `fanout`, `rounds` and `blackboard` once they are registered. The M4 run:

  ```bash
  APL_MODEL=openai:gpt-6-luna uv run apl run \
    --arch react,mapstate,mapstate_routes,hybrid,fanout,rounds,blackboard \
    --level all --seeds dev --limit 1 [--execute]
  ```

- **Order**: level → seed → repeat → architecture.
- **Dry run**: a `code` line follows `prompt`:

  ```text
    code           af49452
    code           af49452 (uncommitted changes: this run cannot be continued)
  ```

  The commit is `unknown` outside git.
- **Bounds**: the tokens and cost lines stay hard upper bounds (episodes × token cap). The model-calls
  line is labelled `model calls (est.)`, because A6's re-asks and the orchestrators' extra calls are
  not tied to steps.
- **Execute**: stops after 3 infrastructure-error episodes in a row (exit code 4).

## `apl continue RUN_DIR [--execute]` (new)

### Dry run

```text
Continue run 20261031-210000-react+mapstate+mapstate_routes+hybrid+fanout+rounds+blackboard (dry run, nothing is sent or written)
  done           12 of 21 episodes
  left           9
  next           rounds L2 1000 r1
  model          openai:gpt-6-luna
  code           af49452
At most
  model calls (est.)  ...
  tokens         18,000,000
  cost           $...
Run with --execute to continue it (a paid provider then costs money).
```

If the last line of `episodes.jsonl` was cut off, the dry run says
`a cut-off last row will be removed` and changes nothing.

### Refusals (exit code 2, nothing played or written)

| Condition | Message (one line per difference) |
| --- | --- |
| No `run.json` / malformed row | as `apl report` |
| Setting differs | `setting <name> differs (run: <a>, now: <b>)` |
| Package version differs | `version of <package> differs (run: <a>, now: <b>)` |
| Commit differs | `commit differs (run: <a>, now: <b>)` |
| Tree dirty now | `the working tree has uncommitted changes; commit or stash them` |
| Run started dirty | `the run was started with uncommitted changes; it cannot be continued` |
| Architecture unknown or not written | as `apl run` |

All refusals are printed together, prefixed `apl: cannot continue <run-id>:`.

### Already complete (exit code 0)

`run <run-id> is already complete; nothing to play.` Nothing is written.

### Every episode done, run not marked complete (exit code 0)

For example after a crash between the last row and `run.json`. The dry run prints
`run <run-id>: every episode has a row; --execute marks the run complete and writes report.md.`
With `--execute`, nothing is played: `run.json` gets `completed: true` and `ended`, and
`report.md` is written and printed.

### Execute

- Removes a cut-off last row (only after every check passed), plays the missing episodes in run
  order into the same folder, sets `completed: true` and `ended`, rewrites and prints `report.md`.
- Progress lines are numbered within the whole run: `[13/21] rounds L2 1000 r1 ...`.

## Exit codes (`apl run --execute` and `apl continue --execute`)

| Exit code | When |
| --- | --- |
| 0 | Finished, report written |
| 2 | Bad arguments, a missing key, an unwritten architecture, or a refusal to continue |
| 3 | The provider rejected a request permanently (M2) |
| 4 | Stopped after 3 infrastructure errors in a row; `run.json` stays incomplete |
| 130 | Interrupted (Ctrl-C); finished episodes are kept |

After exit codes 3, 4 and 130 the command prints `continue with: uv run apl continue <RUN_DIR> --execute`.
