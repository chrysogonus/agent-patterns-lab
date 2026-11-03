"""The rune floor's outputs, pinned before the workshop was added (specs/011 T002, SC-001).

`GOLDEN_REGEN=1` rewrites the expected file, only for a deliberate change of this output.
"""

import os
from pathlib import Path

from apl.rune.prompt import prompt_fingerprint
from apl.runner.settings import Settings
from apl.runner.spec import RunSpec, format_plan

FIXTURES = Path(__file__).parent / "fixtures"
CODE = {"commit": "30fffdf0000000000000000000000000000000000", "dirty": False}


def test_the_rune_prompt_fingerprint_is_unchanged() -> None:
    assert prompt_fingerprint() == "7c213929b31a"


def test_the_rune_dry_run_plan_is_unchanged() -> None:
    spec = RunSpec.build(["react"], ["all"], "dev", limit=1, problem="rune")
    text = format_plan(spec, Settings(), {"react": True}, CODE) + "\n"
    path = FIXTURES / "rune-plan.txt"
    if os.environ.get("GOLDEN_REGEN"):
        path.write_text(text, encoding="utf-8")
    assert text == path.read_text(encoding="utf-8")
