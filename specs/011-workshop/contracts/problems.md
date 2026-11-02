# Contract: The Problem Table

Adds to specs/010 `contracts/problems.md`.

```python
PROBLEMS["workshop"] = Problem(
    name="workshop",
    levels=workshop.LEVELS,              # W1, W2, W3
    dev_seeds=range(1000, 1010),
    test_seeds=range(2000, 2020),
    generate=workshop.generate,          # random.Random(f"workshop:{level}:{seed}")
    reference_steps=lambda w: w.reference,
    start_episode=workshop.start_episode,
    build_kit=<apl.workshop.kit.build_kit>,   # imported lazily, as the others
    prompt_fingerprint=<apl.workshop.prompt.prompt_fingerprint>,
    max_attempts=workshop.env.MAX_ATTEMPTS,   # 3
)
```

The kit: `problem="workshop"`, `start` = the start view's result, `add_scout` returns None,
`restart` and `max_attempts` as on the rune floor.

Allowed architecture imports (test and AGENTS.md): add `apl.workshop.tools`,
`apl.workshop.results`.
