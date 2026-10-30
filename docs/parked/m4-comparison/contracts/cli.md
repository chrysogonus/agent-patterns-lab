# Contract: CLI changes for M3

This contract adds to specs/002-runner-react/contracts/cli.md. Everything not listed here is
unchanged.

## `apl run`

- `--arch` accepts `mapstate` once it is registered. The comparison run:

  ```bash
  uv run apl run --arch react,mapstate --level all --seeds dev --repeats 3 [--execute]
  ```

- **Order**: episodes are played level → seed → repeat → architecture (research R8). The
  progress lines therefore alternate `react` and `mapstate`.
- **Dry run**: a new `code` line comes after `prompt`:

  ```text
    code           3f2a9c1
    code           3f2a9c1 (uncommitted changes: this run cannot be continued)
  ```

  The second form appears when the tree is dirty. The commit is `unknown` outside git.
- **Execute**: stops after 3 infrastructure-error episodes in a row (research R11).

## `apl continue RUN_DIR [--execute]` (new)

### Dry run (no `--execute`)

```text
Continue run 20261031-220000-react+mapstate (dry run, nothing is sent or written)
  done           112 of 180 episodes
  left           68
  next           mapstate L3 1002 r2
  model          ollama:qwen3:8b
  code           3f2a9c1
At most
  model calls    4,488
  tokens         40,800,000
  cost           no estimate (set APL_PRICE_INPUT and APL_PRICE_OUTPUT)
Run with --execute to continue it (a paid provider then costs money).
```

If the last line of `episodes.jsonl` was cut off, the dry run says
`a cut-off last row will be removed` and changes nothing. `--execute` removes it, but only after
every check below has passed. A refusal leaves the file as it is.

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

### Execute

- Progress lines are numbered within the whole run: `[113/180] mapstate L3 1002 r2 ...`.
- New rows and files go to the same folder. At the end, `run.json` gets `completed: true` and
  `ended`, and `report.md` is rewritten and printed.

## Exit codes (`apl run --execute` and `apl continue --execute`)

| Exit code | When |
| --- | --- |
| 0 | Finished, report written |
| 2 | Bad arguments, a missing key, an unwritten architecture, or a refusal to continue |
| 3 | The provider rejected a request permanently (M2) |
| 4 | Stopped after 3 infrastructure errors in a row; `run.json` stays incomplete |
| 130 | Interrupted (Ctrl-C); finished episodes are kept, and the run can be continued |

After exit code 3, 4 or 130, the command prints the line
`continue with: uv run apl continue <RUN_DIR> --execute`.
