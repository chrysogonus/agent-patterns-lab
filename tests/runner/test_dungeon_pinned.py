"""The dungeon's outputs, pinned before the survey field was added (specs/005 SC-001, R16).

The plan text and the M4 report must stay byte for byte the same. `GOLDEN_REGEN=1` rewrites the
expected files, only for a deliberate change of these outputs.
"""

import os
from pathlib import Path

from apl.kit import prompt_fingerprint
from apl.runner.report import load_run, render
from apl.runner.settings import Settings
from apl.runner.spec import RunSpec, format_plan

FIXTURES = Path(__file__).parent / "fixtures"
CODE = {"commit": "30fffdf0000000000000000000000000000000000", "dirty": False}


def _check(name: str, text: str) -> None:
    path = FIXTURES / name
    if os.environ.get("GOLDEN_REGEN"):
        path.write_text(text, encoding="utf-8")
    assert text == path.read_text(encoding="utf-8")


def test_the_dungeon_prompt_fingerprint_is_unchanged() -> None:
    assert prompt_fingerprint() == "ff9afb3b9f66"


def test_the_dungeon_dry_run_plan_is_unchanged() -> None:
    spec = RunSpec.build(["react"], ["all"], "dev", limit=2)
    _check("dungeon-plan.txt", format_plan(spec, Settings(), {"react": True}, CODE) + "\n")


def test_the_m4_report_is_unchanged() -> None:
    _check("m4-report.md", render([load_run(FIXTURES / "m4-run")]))
