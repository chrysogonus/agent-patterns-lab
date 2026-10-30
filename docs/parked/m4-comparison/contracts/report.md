# Contract: Comparison sections in the report

This contract adds to specs/002-runner-react/contracts/results.md ("Report"). The existing
header, main table, spread table, error table and notes are unchanged.

## When the sections appear

They appear when the completed rows of the reported runs cover **exactly two** architectures:

- **a** is the baseline: the first of them in the first run's `architectures`;
- **b** is the other one.

With one architecture, or with three or more, the report is as in M2.

## Comparison by level (FR-012)

```markdown
## Comparison: mapstate vs react

> Development result (dev seeds). Must not be reported.

| Level | Metric | react | mapstate | mapstate − react |
| --- | --- | --- | --- | --- |
| L1 | Success | 70% (60–80%) | 90% (80–100%) | +20 pp |
| L1 | Efficiency (median) | 0.50 (0.44–0.57) | 0.67 (0.57–0.80) | +0.17 |
| L1 | Tokens (median) | 48,210 (40,100–55,900) | 15,300 (14,200–17,000) | −32,910 |
| L1 | Latency (median) | 61.2s (55.0–70.3s) | 38.4s (35.1–41.0s) | −22.8s |
| L2 | ... |
```

- Each value is computed over all completed episodes of that architecture and level. The value in
  parentheses is the min–max of the same statistic computed per repeat.
- Success is shown in whole percent and its difference in percentage points (`pp`). Efficiency
  has two decimals. Tokens are whole numbers with thousands separators. Latency has one decimal
  and an `s`.
- `—` stands for a value without data. A difference involving `—` is `—`.
- The notice line is the one from the report header: the dev or the test variant (FR-015).

## Per dungeon (FR-013, FR-014)

```markdown
## Per dungeon: mapstate vs react

| Level | Seeds | Success: higher / same / lower | p | Efficiency: higher / same / lower | p | Left out |
| --- | --- | --- | --- | --- | --- | --- |
| L1 | 10 | 4 / 6 / 0 | 0.125 | 5 / 2 / 1 | 0.219 | 0 |
| L2 | 10 | ... |

Counts are seeds where mapstate's value is higher, the same or lower than react's, over the
repeats both completed. Efficiency counts only seeds both solved at least once. p is a two-sided
exact sign test with ties dropped. With 10 seeds the smallest possible p is 0.002, and it
describes these seeds only.
```

The columns are:

- **Seeds**: the number of seeds with at least one kept pair.
- **Success**: the higher / same / lower counts, then the p-value. p is written with three
  decimals, or `—` when there is no non-tied seed.
- **Efficiency**: the higher / same / lower counts, then the p-value, in the same format.
- **Left out**: the number of left-out (seed, repeat) pairs.

When "Left out" is above 0, a line follows the table:
`Left out: L2 1003 r2 (mapstate: infrastructure error), ...`.

## Stability

The same rows give the same report, byte for byte. Rows are sorted by level, seed and repeat
before anything is computed. Their order in the file does not matter.
