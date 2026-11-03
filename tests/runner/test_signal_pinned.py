"""The signal trace's outputs, pinned before the rune floor was added (specs/010 T002, SC-001).

`GOLDEN_REGEN=1` rewrites the expected file, only for a deliberate change of this output.
"""

import os
from pathlib import Path

from apl.runner.settings import Settings
from apl.runner.spec import RunSpec, format_plan
from apl.signal_trace.prompt import prompt_fingerprint

FIXTURES = Path(__file__).parent / "fixtures"
CODE = {"commit": "30fffdf0000000000000000000000000000000000", "dirty": False}


def test_the_signal_prompt_fingerprint_is_unchanged() -> None:
    assert prompt_fingerprint() == "4393e09f0471"


def test_the_signal_dry_run_plan_is_unchanged() -> None:
    spec = RunSpec.build(["react"], ["all"], "dev", limit=1, problem="signal")
    text = format_plan(spec, Settings(), {"react": True}, CODE) + "\n"
    path = FIXTURES / "signal-plan.txt"
    if os.environ.get("GOLDEN_REGEN"):
        path.write_text(text, encoding="utf-8")
    assert text == path.read_text(encoding="utf-8")
