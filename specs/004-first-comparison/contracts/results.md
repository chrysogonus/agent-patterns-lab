# Contract: Results and report changes for M4

This adds to specs/002-runner-react/contracts/results.md. Everything not listed here is unchanged.
Research R4, R5, R14.

## Outcome (`episodes/<key>.outcome.json`, viewer `outcome.json`)

- Log entries get `"scout": <n>` when the call was made by a scout other than 0.
- The outcome gets `"scouts": <n>` when more than one scout made a tool call.
- Single-agent outcomes are byte for byte as before.

## Conversation (`*.conversation.json`)

- A call entry gets `"role": "orchestrator"` or `"role": "scout N"` when the model call carried that
  metadata. Calls without a role are as before.

## Episode row (`episodes.jsonl`)

Two new fields, written in every new row:

| Field | Type | Meaning |
| --- | --- | --- |
| `scouts` | int or null | Scouts that made at least one tool call (1 for single-agent episodes, 0 if none called a tool); null for infrastructure errors |
| `orchestrator_calls` | int | Model calls with role `orchestrator` (0 for single-agent episodes) |

Rows written before M4 lack both and parse with them as `null`.

## Report: comparison section

Appears after the main table when the completed rows cover two or more architectures. The main
table, the spread table, the error table and the notes are unchanged.

```markdown
## Comparison

> Development result (dev seeds). Must not be reported.

Seeds 1000, 1 repeat. Differences are against the reference architecture in the last column.

### L1

| Arch | Success | Efficiency | Steps | Tokens | Calls: orch / scouts | Latency | Scouts | Δ success | Δ efficiency | Reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| react | 100% | 0.62 | 13 | 41,200 | 0 / 14 | 52.0s | 1 | — | — | — |
| mapstate | 100% | 0.80 | 10 | 18,300 | 0 / 11 | 31.4s | 1 | +0 pp | +0.18 | react |
| ... |
| fanout | 100% | 0.47 | 17 | 60,100 | 1 / 19 | 40.2s | 3 | +0 pp | −0.33 | mapstate |
```

- Rows follow the first run's `architectures` order.
- Values are over the completed episodes of that architecture and level: success in whole percent,
  efficiency with two decimals (median over successes), steps, tokens (input plus output), calls,
  latency and scouts as medians.
- The intro line states the seeds and repeats actually covered, from the run records.
- Δ success is in percentage points, Δ efficiency with two decimals and a sign. Both are `—` when
  the reference has no rows at that level, or when either value is `—`.
- `—` stands for a missing value, including rows written before M4.
- The references:

  | Architecture | Reference |
  | --- | --- |
  | `mapstate` | `react` |
  | `mapstate_routes` | `mapstate` |
  | `hybrid` | `mapstate_routes` |
  | `fanout`, `rounds`, `blackboard` | `mapstate` |

  Any other architecture has no reference (`—`).

## Stability

The same rows give the same report, byte for byte. Rows are sorted by level, seed, repeat and
architecture order before anything is computed.
