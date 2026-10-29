# Contract: Outcome record and episode log

Available from `episode.outcome()` after the episode ends; calling it earlier raises
`RuntimeError`. Not agent-facing. `to_dict()` returns:

```json
{
  "level": "L2",
  "seed": 1003,
  "success": true,
  "end_reason": "exit",
  "steps": 23,
  "optimal_steps": 14,
  "budget": 42,
  "invalid_actions": 3,
  "budget_hit": false,
  "log": [
    {
      "index": 0,
      "step": 1,
      "action": {"tool": "move", "args": ["east"]},
      "result": {"ok": true, "error": null, "data": {"label": "b7", "exits": [], "items": [], "inventory": [], "is_exit": false}}
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `level`, `seed` | From the dungeon; `null` for a hand-built dungeon |
| `success` | `end_reason == "exit"` |
| `end_reason` | `exit`, `budget` or `stopped` |
| `steps` | Counted tool calls |
| `optimal_steps` | The solver's shortest length |
| `budget` | `3 × optimal_steps` |
| `invalid_actions` | Counted calls that returned an error |
| `budget_hit` | `end_reason == "budget"` |
| `log` | Every call in order, including uncounted `episode_over` calls (`step: null`) |

M2 adds model-side fields (`llm_calls`, `tool_calls`, tokens, latency) and the efficiency ratio
to the JSONL row it builds from this record. M1 doesn't define them.
