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
uv run apl dungeon show --level L3 --seed 1000 --route solution  # inspect a dungeon
uv run apl survey show --level S2 --seed 1000  # inspect a survey field
uv run apl signal show --level T2 --seed 1000 --route reference  # inspect a signal trace pipe
uv run apl rune show --level R1 --seed 1000 --route reference  # inspect a rune floor
uv run apl workshop show --level W2 --seed 1000 --route reference  # inspect a workshop
uv run apl warehouse show --level P2 --seed 1000 --route reference  # inspect a warehouse
uv run apl run --arch react --level all --seeds dev --limit 2  # plan a run (free dry run)
uv run apl run --problem survey --arch react --level all --seeds dev --limit 1  # a survey plan
uv run apl run --problem signal --arch react --level all --seeds dev --limit 1  # a signal plan
uv run apl run --problem rune --arch react --level all --seeds dev --limit 1  # a rune plan
uv run apl run --problem workshop --arch react --level all --seeds dev --limit 1  # a workshop plan
uv run apl run --problem warehouse --arch react --level all --seeds dev --limit 1  # a warehouse plan
uv run apl continue results/<run-id>  # plan the rest of an interrupted run (free)
uv run apl serve             # the browser viewer on http://127.0.0.1:8765/
```

All four checks must pass before a feature counts as done.

## Rules

- The user writes the architecture graphs in `src/apl/arch/`. Do not write graph logic there
  unless asked.
- Architectures reach each problem only through its tools: the dungeon's `look`, `move`, `take`
  and `use`, the survey field's `look`, `move` and `submit`, the signal trace's `look`, `probe` and
  `submit`, the rune floor's `look` and `move`, the workshop's `look`, `inspect`, `gather` and
  `craft`, the warehouse's `look`, `move`, `pick` and `drop`. From `apl` they may import only
  `apl.kit`, `apl.dungeon.tools`, `apl.dungeon.results`, `apl.survey.tools`, `apl.survey.results`,
  `apl.signal_trace.tools`, `apl.signal_trace.results`, `apl.rune.tools`, `apl.rune.results`,
  `apl.workshop.tools`, `apl.workshop.results`, `apl.warehouse.tools` and `apl.warehouse.results`,
  and they
  must use `kit.model` instead of creating a model (both enforced by a test).
- No paid model call without an explicit `--execute`. Tests never make paid calls.
- Never commit `.env`; it holds the provider API key.
- Each milestone after M0 is one Spec Kit feature: `/speckit-specify` through
  `/speckit-implement`, then `/speckit-converge`.
