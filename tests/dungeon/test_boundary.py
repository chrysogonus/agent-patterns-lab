"""What an architecture can see and import (SC-007, constitution II)."""

import ast
import json
import random
from pathlib import Path

import pytest

from apl.dungeon import DEV_SEEDS, LEVELS, generate
from apl.dungeon.env import start_episode
from apl.dungeon.tools import AgentTools

ARCH_DIR = Path(__file__).resolve().parents[2] / "src" / "apl" / "arch"
ALLOWED = {"apl.dungeon.tools", "apl.dungeon.results"}

ENVELOPE = {"ok", "error", "data"}
ERROR = {"code", "message"}
DATA_SHAPES = [
    {"label", "exits", "items", "inventory", "is_exit"},
    {"inventory"},
    {"direction", "color"},
]
EXIT = {"direction", "lock"}


def _check_shape(result: dict[str, object]) -> None:
    assert set(result) == ENVELOPE
    error, data = result["error"], result["data"]
    if result["ok"]:
        assert error is None and isinstance(data, dict) and set(data) in DATA_SHAPES
        for exit in data.get("exits", []):
            assert set(exit) == EXIT
    else:
        assert data is None and isinstance(error, dict) and set(error) == ERROR


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_results_show_only_the_current_room(level: str) -> None:
    rng = random.Random(f"boundary:{level}")
    directions = ["north", "east", "south", "west", "up"]
    items = ["red key", "blue key", "green key", "yellow key", "sword"]
    for seed in DEV_SEEDS:
        dungeon = generate(level, seed)
        episode = start_episode(dungeon)
        tools = AgentTools(episode)
        others = set(dungeon.layout.labels.values())
        results = [tools.start]
        for _ in range(200):
            tool = rng.choice(["look", "move", "move", "move", "take", "use"])
            if tool == "look":
                results.append(tools.look())
            elif tool == "move":
                results.append(tools.move(rng.choice(directions)))
            elif tool == "take":
                results.append(tools.take(rng.choice(items)))
            else:
                results.append(tools.use(rng.choice(items), rng.choice(directions)))
            here = dungeon.layout.labels[episode.position]
            data = results[-1].to_dict()
            _check_shape(data)
            text = json.dumps(data)
            assert all(label not in text for label in others - {here})
            for secret in (dungeon.budget, dungeon.solution.length):
                assert f": {secret}" not in text


def test_agent_tools_expose_only_the_four_tools() -> None:
    public = {name for name in dir(AgentTools) if not name.startswith("_")}
    assert public == {"start", "look", "move", "take", "use"}


def _imports(path: Path, package: str) -> set[str]:
    """Absolute names a file in `package` imports, by statement or by string."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), str(path))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            parts = (
                package.split(".")[: len(package.split(".")) - node.level + 1] if node.level else []
            )
            module = ".".join([*parts, *([node.module] if node.module else [])])
            names.update(f"{module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # A module named in a string is a dynamic import, e.g. importlib.import_module(...).
            if node.value == "apl.dungeon" or node.value.startswith("apl.dungeon."):
                names.add(node.value)
    return names


def _reaches_episode(path: Path) -> bool:
    """AgentTools keeps its Episode in `_episode`; reaching it bypasses the four tools."""
    for node in ast.walk(ast.parse(path.read_text(), str(path))):
        if isinstance(node, ast.Attribute) and node.attr == "_episode":
            return True
        if isinstance(node, ast.Constant) and node.value == "_episode":
            return True
    return False


def _forbidden(root: Path, package: str = "apl.arch") -> list[str]:
    found = []
    for path in sorted(root.rglob("*.py")):
        file_package = ".".join([package, *path.parent.relative_to(root).parts])
        for name in sorted(_imports(path, file_package)):
            if name == "apl.dungeon" or name.startswith("apl.dungeon."):
                if not any(name == a or name.startswith(f"{a}.") for a in ALLOWED):
                    found.append(f"{path.name}: {name}")
        if _reaches_episode(path):
            found.append(f"{path.name}: _episode")
    return found


def test_architectures_import_only_the_agent_surface() -> None:
    if not ARCH_DIR.exists():
        pytest.skip("src/apl/arch/ does not exist yet; this test guards it from M2 on")
    assert _forbidden(ARCH_DIR) == []


def test_boundary_scan_catches_forbidden_imports(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text(
        "from apl.dungeon.tools import AgentTools\nfrom apl.dungeon import results, tools\n"
    )
    (tmp_path / "peek.py").write_text("from apl.dungeon import solver\nimport apl.dungeon.env\n")
    (tmp_path / "rel_ok.py").write_text(
        "from ..dungeon import tools\nfrom ..dungeon.results import ToolResult\nfrom . import x\n"
    )
    (tmp_path / "rel_peek.py").write_text("from ..dungeon import solver\n")
    (tmp_path / "graphs").mkdir()
    (tmp_path / "graphs" / "deep.py").write_text("from ...dungeon.generator import generate\n")
    (tmp_path / "sneak_attr.py").write_text("def f(tools):\n    return tools._episode.dungeon\n")
    (tmp_path / "sneak_getattr.py").write_text("def f(t):\n    return getattr(t, '_episode')\n")
    (tmp_path / "dyn_peek.py").write_text(
        "import importlib\nsolver = importlib.import_module('apl.dungeon.solver')\n"
        "env = __import__('apl.dungeon.env')\n"
    )
    (tmp_path / "dyn_ok.py").write_text(
        "import importlib\ntools = importlib.import_module('apl.dungeon.tools')\n"
    )
    assert _forbidden(tmp_path) == [
        "dyn_peek.py: apl.dungeon.env",
        "dyn_peek.py: apl.dungeon.solver",
        "deep.py: apl.dungeon.generator.generate",
        "peek.py: apl.dungeon.env",
        "peek.py: apl.dungeon.solver",
        "rel_peek.py: apl.dungeon.solver",
        "sneak_attr.py: _episode",
        "sneak_getattr.py: _episode",
    ]
