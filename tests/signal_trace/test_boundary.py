"""What a signal-trace result can show (specs/009 research R14, contracts/signal-tools.md)."""

import dataclasses
import json
import random

import pytest

from apl.signal_trace import DEV_SEEDS, LEVELS, generate, start_episode
from apl.signal_trace.tools import AgentTools

ENVELOPE = {"ok", "error", "data"}
SHAPES = [
    {"segments", "runs"},
    {"segment", "water"},
    {"submitted"},
    {"submitted", "correct", "attempts_left"},
]


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_results_have_fixed_shapes_and_true_answers(level: str) -> None:
    rng = random.Random(f"signal-boundary:{level}")
    for seed in DEV_SEEDS:
        pipe = generate(level, seed)
        episode = start_episode(pipe)
        episode.max_attempts = 3
        tools = AgentTools(episode)
        for _ in range(300):
            tool = rng.choice(["look", "probe", "probe", "probe", "probe", "submit"])
            raw: object = rng.choice([rng.randint(0, pipe.segments + 1), "S", 1.5, "x"])
            if tool == "look":
                result = tools.look()
            elif tool == "probe":
                result = tools.probe(raw)
            else:
                result = tools.submit(raw)
            data = result.to_dict()
            assert set(data) == ENVELOPE
            if data["ok"]:
                assert isinstance(data["data"], dict) and set(data["data"]) in SHAPES
                if tool == "probe":
                    assert data["data"]["water"] == pipe.wet(data["data"]["segment"])
            else:
                error = data["error"]
                assert data["data"] is None and isinstance(error, dict)
                assert set(error) == {"code", "message"}


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_the_layout_does_not_depend_on_the_break(level: str) -> None:
    pipe = generate(level, 1000)
    seen = set()
    for broken in range(1, pipe.segments + 1):
        tools = AgentTools(start_episode(dataclasses.replace(pipe, broken=broken)))
        seen.add((json.dumps(tools.start.to_dict()), json.dumps(tools.look().to_dict())))
    assert len(seen) == 1


def test_agent_tools_expose_only_the_three_tools() -> None:
    public = {name for name in dir(AgentTools) if not name.startswith("_")}
    assert public == {"start", "look", "probe", "submit"}
