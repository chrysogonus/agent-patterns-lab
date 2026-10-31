"""Single-agent episodes, pinned before M4 added scouts (specs/004 SC-001, FR-005).

Every dev dungeon is played by the four single-agent architectures with scripted models; the
outcome and frame JSON must stay byte for byte the same. `GOLDEN_REGEN=1` rewrites the hashes,
only for a deliberate change of these files.
"""

import hashlib
import json
import os
from pathlib import Path

from langchain_core.messages import AIMessage

from apl.dungeon import DEV_SEEDS, LEVELS, generate
from apl.dungeon.frames import build_frames
from apl.runner import registry
from apl.runner.episode import play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from tests.runner.scripted import Strategy, replay_solution, scripted_factory

GOLDEN = Path(__file__).with_name("golden.json")


def _strategy(arch: str, level: str, seed: int) -> Strategy:
    if arch == "hybrid":
        return lambda messages: AIMessage("1")
    return replay_solution(generate(level, seed))


def _hash(data: object) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]


def _played() -> dict[str, dict[str, str]]:
    found = {}
    for arch in ("react", "mapstate", "mapstate_routes", "hybrid"):
        for level in sorted(LEVELS):
            for seed in DEV_SEEDS:
                key = EpisodeKey(arch, level, seed, 1)
                factory = scripted_factory(_strategy(arch, level, seed))
                play = registry.load(arch)
                result = play_episode(key, "golden", "dev", Settings(), play, factory)
                assert result.outcome is not None
                outcome = result.outcome.to_dict()
                actions = [e.action for e in result.outcome.log]
                frames = [f.to_dict() for f in build_frames(generate(level, seed), actions)]
                found[key.name] = {"outcome": _hash(outcome), "frames": _hash(frames)}
    return found


def test_single_agent_episodes_are_unchanged() -> None:
    played = _played()
    if os.environ.get("GOLDEN_REGEN") == "1":
        GOLDEN.write_text(json.dumps(played, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    pinned = json.loads(GOLDEN.read_text(encoding="utf-8"))
    changed = sorted(k for k in pinned.keys() | played.keys() if pinned.get(k) != played.get(k))
    assert not changed, f"single-agent episodes changed: {', '.join(changed[:10])}"
