# Quickstart: Checking the Warehouse

No step here calls a model.

1. **Checks**: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
   `uv run mypy` all pass.
2. **A warehouse**: `uv run apl warehouse show --level P2 --seed 1000 --route reference` prints the
   floor, the packages by number, the aisle counts (one aisle empty, one with two), and the
   reference's calls; its length equals the header's reference, and the budget is 3× it.
3. **Other problems unchanged**: `uv run apl survey show --level S2 --seed 1000` and
   `uv run apl workshop show --level W2 --seed 1000 --route reference` print as on the M11 commit;
   the pin tests pass.
4. **Plans**: `uv run apl run --problem warehouse --arch react,mapstate,fanout,rounds,blackboard
   --level all --seeds dev --limit 1` prints the matrix (3 levels × 5 architectures) without
   calling a model; `--arch hybrid` is refused with the message of
   [contracts/cli.md](contracts/cli.md).
5. **Viewer**: `uv run apl serve`, pick the warehouse, P2, seed 1000: the floor, the dock, D and
   three packages; with "Agent's view" on, every aisle is fogged and its packages hidden. The About
   card shows the chosen architecture on the warehouse. A test seed is refused.
6. **Replay**: the scripted episodes the tests save under a temporary results folder replay with
   the robots in the scout colors, carried packages moving with them, and the delivered count,
   parallel turns and idle robot-turns in the stats panel.
