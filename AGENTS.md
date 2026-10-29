# AGENTS.md

A lab for comparing hand-built LangGraph agent architectures on a generated dungeon, scored by
code. The design and milestones are in `plan.md`. The rules every change must follow are in
`.specify/memory/constitution.md`.

## Commands

```bash
uv sync                      # install the environment
uv run pytest                # tests
uv run ruff check .          # lint
uv run ruff format --check . # formatting
uv run mypy                  # type check (strict)
```

All four checks must pass before a feature counts as done.

## Rules

- The user writes the architecture graphs in `src/apl/arch/`. Do not write graph logic there
  unless asked.
- Architectures reach the dungeon only through `look`, `move`, `take` and `use`.
- No paid model call without an explicit `--execute`. Tests never make paid calls.
- Never commit `.env`; it holds the provider API key.
- Each milestone after M0 is one Spec Kit feature: `/speckit-specify` through
  `/speckit-implement`, then `/speckit-converge`.
