# Contract: The Problem Table

Adds to specs/009 `contracts/problems.md`.

```python
PROBLEMS["rune"] = Problem(
    name="rune",
    levels=rune.LEVELS,                  # R0, R1, R2, R3
    dev_seeds=range(1000, 1010),
    test_seeds=range(2000, 2020),
    generate=rune.generate,              # random.Random(f"rune:{level}:{seed}")
    reference_steps=lambda floor: floor.reference,
    start_episode=rune.start_episode,
    build_kit=<apl.rune.kit.build_kit>,  # imported lazily, as the others
    prompt_fingerprint=<apl.rune.prompt.prompt_fingerprint>,
    max_attempts=rune.env.MAX_ATTEMPTS,  # 3
)
```

The kit: `problem="rune"`, `start` = the floor result, `add_scout` returns None, `restart` and
`max_attempts` as on the signal trace.

Allowed architecture imports (test and AGENTS.md): add `apl.rune.tools`, `apl.rune.results`.
