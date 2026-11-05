"""The workshop's outputs, pinned before the warehouse was added (specs/012 T002, SC-001).

`GOLDEN_REGEN=1` rewrites the expected file, only for a deliberate change of this output.
"""

import os
from pathlib import Path

from apl.runner.settings import Settings
from apl.runner.spec import RunSpec, format_plan
from apl.workshop.prompt import prompt_fingerprint

FIXTURES = Path(__file__).parent / "fixtures"
CODE = {"commit": "30fffdf0000000000000000000000000000000000", "dirty": False}


def test_the_workshop_prompt_fingerprint_is_unchanged() -> None:
    assert prompt_fingerprint() == "d07e651ad0af"


def test_the_workshop_dry_run_plan_is_unchanged() -> None:
    spec = RunSpec.build(["react"], ["W1", "W2", "W3"], "dev", limit=1, problem="workshop")
    text = format_plan(spec, Settings(), {"react": True}, CODE) + "\n"
    path = FIXTURES / "workshop-plan.txt"
    if os.environ.get("GOLDEN_REGEN"):
        path.write_text(text, encoding="utf-8")
    assert text == path.read_text(encoding="utf-8")
