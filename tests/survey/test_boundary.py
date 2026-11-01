"""What a survey result can show (specs/005 SC-005, contracts/survey-tools.md)."""

import json
import random

import pytest

from apl.survey import DEV_SEEDS, LEVELS, generate, start_episode
from apl.survey.model import cell_name
from apl.survey.tools import AgentTools

ENVELOPE = {"ok", "error", "data"}
SHAPES = [{"cell", "deposit", "exits", "columns", "rows"}, {"submitted"}]


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_results_show_only_the_current_cell(level: str) -> None:
    rng = random.Random(f"survey-boundary:{level}")
    for seed in DEV_SEEDS:
        field = generate(level, seed)
        episode = start_episode(field)
        tools = AgentTools(episode)
        results = [tools.start]
        for _ in range(300):
            tool = rng.choice(["look", "move", "move", "move", "move", "submit"])
            if tool == "look":
                results.append(tools.look())
            elif tool == "move":
                results.append(tools.move(rng.choice(["north", "east", "south", "west", "up"])))
            else:
                results.append(tools.submit(rng.choice([-1, "x", 1.5])))
            data = results[-1].to_dict()
            assert set(data) == ENVELOPE
            if data["ok"]:
                assert isinstance(data["data"], dict) and set(data["data"]) in SHAPES
            else:
                error = data["error"]
                assert data["data"] is None and isinstance(error, dict)
                assert set(error) == {"code", "message"}
            # The field's size is public (research R6); any other number could be a secret.
            sizes = ("columns", "rows")
            view = data["data"] if isinstance(data["data"], dict) else {}
            text = json.dumps(data | {"data": {k: v for k, v in view.items() if k not in sizes}})
            here = cell_name(episode.scouts[0])
            others = {cell_name(c) for c in field.all_cells()} - {here}
            assert all(f'"{name}"' not in text for name in others)
            for secret in (field.budget, field.reference_steps, field.true_total):
                assert f": {secret}," not in text and f": {secret}}}" not in text


def test_agent_tools_expose_only_the_three_tools() -> None:
    public = {name for name in dir(AgentTools) if not name.startswith("_")}
    assert public == {"start", "look", "move", "submit"}
