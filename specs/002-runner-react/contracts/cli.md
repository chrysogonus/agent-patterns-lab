# Contract: `apl run` and `apl report`

## `apl run`

```text
apl run --arch NAME[,NAME...] --level L[,L...] --seeds dev|test [--limit K] [--only S[,S...]]
        [--repeats N] [--execute]
```

| Option | Meaning |
| --- | --- |
| `--arch` | Registered architecture names (`react`). Unknown: exit 2, listing the registered names. Registered but not written yet: the dry run still prints the plan, marked `(not written yet)`; `--execute` refuses with exit 2 |
| `--level` | `L1`, `L2`, `L3`, comma-separated, or `all` |
| `--seeds` | The seed set, `dev` or `test` |
| `--limit K` | Use only the first K seeds of the set (1 ≤ K ≤ set size) |
| `--only S,...` | Use only these seeds; each must be in the set. Not combinable with `--limit` |
| `--repeats N` | Repeats per (architecture, level, seed); default 1, N ≥ 1 |
| `--execute` | Actually run. Without it, print the plan only |

Order of episodes: architecture, then level, then seed, then repeat.

### Dry run (no `--execute`)

Prints, and does nothing else (no network, no files; FR-013, SC-001):

```text
Plan (dry run, nothing is sent or written)
  architectures  react
  levels         L1, L2, L3
  seeds          dev: 1000, 1001 (2 of 10)  -> development only, must not be reported
  repeats        1
  episodes       6
  model          openai:gpt-6-luna
  temperature    provider default
  reasoning      provider default
  token cap      600,000 per episode
  prompt         a1b2c3d4e5f6
At most
  model calls    228
  tokens         3,600,000
  cost           $1.80 (at $0.10 / $0.50 per 1M tokens)
Run with --execute to spend money.
```

Without prices: `cost  no estimate (set APL_PRICE_INPUT and APL_PRICE_OUTPUT)`. With test seeds:
`-> for reporting`.

### Execute

1. Checks the provider key (research R11). Missing: exit 2, `apl: OPENAI_API_KEY is not set (needed
   for openai:gpt-6-luna)`.
2. Creates the run folder and writes `run.json` with `completed: false`.
3. Plays the episodes, printing one line per episode:
   `[4/6] react L2 1001 r1  exit  steps 30/36 (optimal 12)  calls 30  tokens 212,431  41.2s`.
4. Sets `completed: true` and the end time in `run.json`, prints the folder path, and builds the
   report for this run (as `apl report <folder>`).

| Exit code | When |
| --- | --- |
| 0 | Dry run printed, or every episode finished (with any outcome, including infrastructure errors) |
| 2 | Invalid arguments, missing key |
| 3 | The provider rejected a request permanently; the run stops, `run.json` stays `completed: false` |
| 130 | Interrupted (Ctrl-C); finished rows are kept, `completed: false` |

## `apl report`

```text
apl report RUN_DIR [RUN_DIR ...]
```

- Builds the report (contracts/results.md) and prints it.
- One run: writes `RUN_DIR/report.md`. Several: writes `results/report-<YYYYMMDD-HHMMSS>.md`.
- Exit 2 for a folder without `run.json` or with malformed rows, and for incompatible runs, with the
  reason (FR-030, FR-031):
  `apl: cannot combine runs: model differs (openai:gpt-6-luna vs openai:gpt-6-sol)`.

## `apl dungeon show` (unchanged)

`--route results/<run>/episodes/<file>.outcome.json` draws and animates a recorded episode
(FR-024). The level and seed are given as before and must match the file's `level` and `seed`.
