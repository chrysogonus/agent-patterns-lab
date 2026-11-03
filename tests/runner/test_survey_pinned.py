"""The survey field's outputs, pinned before the signal trace was added (specs/009 T002, SC-001).

`GOLDEN_REGEN=1` rewrites the expected file, only for a deliberate change of this output.
"""

import os
from pathlib import Path

from apl.runner.settings import Settings
from apl.runner.spec import RunSpec, format_plan
from apl.survey.prompt import prompt_fingerprint

FIXTURES = Path(__file__).parent / "fixtures"
CODE = {"commit": "30fffdf0000000000000000000000000000000000", "dirty": False}


def test_the_survey_prompt_fingerprint_is_unchanged() -> None:
    assert prompt_fingerprint() == "ed75d3273f56"


def test_the_survey_dry_run_plan_is_unchanged() -> None:
    spec = RunSpec.build(["react"], ["all"], "dev", limit=1, problem="survey")
    text = format_plan(spec, Settings(), {"react": True}, CODE) + "\n"
    path = FIXTURES / "survey-plan.txt"
    if os.environ.get("GOLDEN_REGEN"):
        path.write_text(text, encoding="utf-8")
    assert text == path.read_text(encoding="utf-8")
