# Contract: The Problem Table

Adds to specs/011 `contracts/problems.md`.

```python
PROBLEMS["warehouse"] = Problem(
    name="warehouse",
    levels=warehouse.LEVELS,             # P1, P2, P3
    dev_seeds=range(1000, 1010),
    test_seeds=range(2000, 2020),
    generate=warehouse.generate,         # random.Random(f"warehouse:{level}:{seed}")
    reference_steps=lambda f: f.reference_steps,
    start_episode=warehouse.start_episode,
    build_kit=<apl.warehouse.kit.build_kit>,   # imported lazily, as the others
    prompt_fingerprint=<apl.warehouse.prompt.prompt_fingerprint>,
    max_attempts=warehouse.env.MAX_ATTEMPTS,   # 1: no retrying architecture plays it
)
```

The kit: `problem="warehouse"`, `start` = the start view's result, `tool_node` drives robot 0,
`add_scout` adds a robot on the dock (None after 4) with its own tool node and start view,
`restart` returns False, `max_attempts` 1. Calls from parallel branches are serialized by a lock,
as on the survey field.

Registry: `SUPPORTS` gains `"warehouse"` for `react`, `mapstate`, `fanout`, `rounds`, `blackboard`.

Allowed architecture imports (boundary test and AGENTS.md): add `apl.warehouse.tools`,
`apl.warehouse.results`.
