# Contract: The Problem Table

Adds to specs/005 `contracts/problems.md`.

```python
PROBLEMS["signal"] = Problem(
    name="signal",
    levels=signal_trace.LEVELS,          # T1, T2, T3
    dev_seeds=range(1000, 1010),
    test_seeds=range(2000, 2020),
    generate=signal_trace.generate,      # random.Random(f"signal:{level}:{seed}")
    reference_steps=lambda pipe: pipe.reference_steps,
    start_episode=signal_trace.start_episode,
    build_kit=<apl.signal_trace.kit.build_kit>,   # imported lazily, as the survey's
    prompt_fingerprint=<apl.signal_trace.prompt.prompt_fingerprint>,
    max_attempts=signal_trace.env.MAX_ATTEMPTS,   # 3
)
```

The kit: `problem="signal"`, `start` = the layout result, `add_scout` returns None, `restart` and
`max_attempts` as on the survey field.

Allowed architecture imports (test and AGENTS.md): add `apl.signal_trace.tools`,
`apl.signal_trace.results`.
