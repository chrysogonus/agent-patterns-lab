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
# Architectures may import from apl only these (and each other, inside apl.arch).
ALLOWED = {
    "apl.kit", "apl.dungeon.tools", "apl.dungeon.results", "apl.survey.tools",
    "apl.survey.results", "apl.signal_trace.tools", "apl.signal_trace.results",
    "apl.rune.tools", "apl.rune.results", "apl.workshop.tools", "apl.workshop.results",
    "apl.warehouse.tools", "apl.warehouse.results", "apl.arch",
}  # fmt: skip  # each problem's tools and results (constitution 2.5.0, specs/005, /009–/012)
# They must use kit.model, never create a model of their own (Constitution I, research R15).
MODEL_MODULES = (
    "openai",
    "anthropic",
    "langchain_openai",
    "langchain_anthropic",
    "langchain.chat_models",
    "langchain_core.language_models",
)
MODEL_NAMES = {"init_chat_model", "ChatOpenAI", "ChatAnthropic"}

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
            if _within(node.value, ("apl",)):
                names.add(node.value)
    return names


def _within(name: str, modules: tuple[str, ...] | set[str]) -> bool:
    return any(name == m or name.startswith(f"{m}.") for m in modules)


def _model_names(path: Path) -> set[str]:
    """Uses of names that create a model, as in `init_chat_model(...)` or `x.ChatOpenAI(...)`."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text(), str(path))):
        name = node.id if isinstance(node, ast.Name) else getattr(node, "attr", None)
        if name in MODEL_NAMES:
            found.add(f"name {name}")
    return found


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
            if _within(name, ("apl",)) and not _within(name, ALLOWED):
                found.append(f"{path.name}: {name}")
            elif _within(name, MODEL_MODULES):
                found.append(f"{path.name}: {name}")
        if _reaches_episode(path):
            found.append(f"{path.name}: _episode")
        found += [f"{path.name}: {name}" for name in sorted(_model_names(path))]
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
    (tmp_path / "kit_ok.py").write_text(
        "from apl.kit import Kit\nfrom langgraph.graph import StateGraph\n"
        "from langchain_core.messages import HumanMessage\nfrom . import helpers\n"
    )
    (tmp_path / "model_own.py").write_text(
        "from langchain.chat_models import init_chat_model\nm = init_chat_model('openai:x')\n"
    )
    (tmp_path / "model_sdk.py").write_text(
        "import openai\nfrom langchain_openai import ChatOpenAI\n"
    )
    (tmp_path / "model_attr.py").write_text("import langchain_x as lc\nm = lc.ChatAnthropic()\n")
    (tmp_path / "runner_peek.py").write_text("from apl.runner import registry\nimport apl\n")
    assert _forbidden(tmp_path) == [
        "dyn_peek.py: apl.dungeon.env",
        "dyn_peek.py: apl.dungeon.solver",
        "deep.py: apl.dungeon.generator.generate",
        "model_attr.py: name ChatAnthropic",
        "model_own.py: langchain.chat_models.init_chat_model",
        "model_own.py: name init_chat_model",
        "model_sdk.py: langchain_openai.ChatOpenAI",
        "model_sdk.py: openai",
        "peek.py: apl.dungeon.env",
        "peek.py: apl.dungeon.solver",
        "rel_peek.py: apl.dungeon.solver",
        "runner_peek.py: apl",
        "runner_peek.py: apl.runner.registry",
        "sneak_attr.py: _episode",
        "sneak_getattr.py: _episode",
    ]


def test_the_orchestrators_are_scanned_and_use_kit_model() -> None:  # specs/004 acceptance 2.6
    scanned = {p.name for p in ARCH_DIR.rglob("*.py")}
    assert {"scouts.py", "fanout.py", "rounds.py", "blackboard.py"} <= scanned
    assert "kit.model" in (ARCH_DIR / "scouts.py").read_text()  # scouts and orchestrators call it


def test_the_survey_field_internals_are_forbidden_too(tmp_path: Path) -> None:  # specs/005 US4
    (tmp_path / "ok.py").write_text(
        "from apl.survey.tools import AgentTools\nfrom apl.survey.results import ToolResult\n"
    )
    (tmp_path / "peek.py").write_text(
        "from apl.survey.generator import generate\nimport apl.survey.env\n"
        "from apl.survey import walk\nfrom apl.problems import get\n"
    )
    assert _forbidden(tmp_path) == [
        "peek.py: apl.problems.get",
        "peek.py: apl.survey.env",
        "peek.py: apl.survey.generator.generate",
        "peek.py: apl.survey.walk",
    ]


def test_the_signal_trace_internals_are_forbidden_too(tmp_path: Path) -> None:  # specs/009 US4
    (tmp_path / "ok.py").write_text(
        "from apl.signal_trace.tools import AgentTools\n"
        "from apl.signal_trace.results import ToolResult\n"
    )
    (tmp_path / "peek.py").write_text(
        "from apl.signal_trace.generator import generate\nimport apl.signal_trace.env\n"
        "from apl.signal_trace import strategy\nfrom apl.signal_trace.model import Pipe\n"
    )
    assert _forbidden(tmp_path) == [
        "peek.py: apl.signal_trace.env",
        "peek.py: apl.signal_trace.generator.generate",
        "peek.py: apl.signal_trace.model.Pipe",
        "peek.py: apl.signal_trace.strategy",
    ]


def test_the_rune_floor_internals_are_forbidden_too(tmp_path: Path) -> None:  # specs/010 US4
    (tmp_path / "ok.py").write_text(
        "from apl.rune.tools import AgentTools\nfrom apl.rune.results import ToolResult\n"
    )
    (tmp_path / "peek.py").write_text(
        "from apl.rune.generator import generate\nimport apl.rune.env\n"
        "from apl.rune import rules\nfrom apl.rune.model import Floor\n"
    )
    assert _forbidden(tmp_path) == [
        "peek.py: apl.rune.env",
        "peek.py: apl.rune.generator.generate",
        "peek.py: apl.rune.model.Floor",
        "peek.py: apl.rune.rules",
    ]


def test_the_workshop_internals_are_forbidden_too(tmp_path: Path) -> None:  # specs/011 US4
    (tmp_path / "ok.py").write_text(
        "from apl.workshop.tools import AgentTools\nfrom apl.workshop.results import ToolResult\n"
    )
    (tmp_path / "peek.py").write_text(
        "from apl.workshop.generator import generate\nimport apl.workshop.env\n"
        "from apl.workshop import plans\nfrom apl.workshop.model import Workshop\n"
    )
    assert _forbidden(tmp_path) == [
        "peek.py: apl.workshop.env",
        "peek.py: apl.workshop.generator.generate",
        "peek.py: apl.workshop.model.Workshop",
        "peek.py: apl.workshop.plans",
    ]


def test_the_warehouse_internals_are_forbidden_too(tmp_path: Path) -> None:  # specs/012 US4
    (tmp_path / "ok.py").write_text(
        "from apl.warehouse.tools import AgentTools\nfrom apl.warehouse.results import ToolResult\n"
    )
    (tmp_path / "peek.py").write_text(
        "from apl.warehouse.generator import generate\nimport apl.warehouse.env\n"
        "from apl.warehouse import plans\nfrom apl.warehouse.model import Floor\n"
    )
    assert _forbidden(tmp_path) == [
        "peek.py: apl.warehouse.env",
        "peek.py: apl.warehouse.generator.generate",
        "peek.py: apl.warehouse.model.Floor",
        "peek.py: apl.warehouse.plans",
    ]
