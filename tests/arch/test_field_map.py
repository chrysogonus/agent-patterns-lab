"""The survey field map, built from tool results only (specs/005 contracts/architectures.md)."""

import json

from apl.arch.field_map import FieldMap


def _view(cell: str, deposit: bool, exits: list[str]) -> dict[str, object]:
    data = {"cell": cell, "deposit": deposit, "exits": exits, "columns": 6, "rows": 6}
    return {"ok": True, "error": None, "data": data}


EXAMPLE = """\
Your map (built from your tool results so far):
You are in: C2. Field: 6 columns (A–F) × 6 rows (1–6).
   A B C D E F
1  . o . ? ? ?
2  . . @ ? ? ?
3  ? ? ? ? ? ?
4  ? ? ? ? ? ?
5  ? ? ? ? ? ?
6  ? ? ? ? ? ?
@ you, o deposit, . seen without deposit, ? not seen yet.
Cells seen: 6 of 36. Deposits seen: 1.
Walls seen: B2 east.
Unseen cells next to seen ones: D1, D2, A3, B3, C3."""


def _example() -> FieldMap:
    found = FieldMap.from_start(json.dumps(_view("A1", False, ["east", "south"])))
    for cell, deposit, exits in [
        ("A2", False, ["north", "east", "south"]),
        ("B2", False, ["north", "south", "west"]),
        ("B1", True, ["east", "south", "west"]),
        ("C1", False, ["east", "south", "west"]),
        ("C2", False, ["north", "east", "south"]),
    ]:
        found.apply("move", {"direction": "east"}, _view(cell, deposit, exits))
    return found


def test_the_contract_example() -> None:
    assert _example().render() == EXAMPLE


def test_failed_calls_and_submissions_change_nothing() -> None:
    found = _example()
    before = found.render()
    found.apply("move", {"direction": "north"}, {"ok": False, "error": {}, "data": None})
    found.apply("submit", {"total": 3}, {"ok": True, "error": None, "data": {"submitted": 3}})
    assert found.render() == before


def test_standing_on_a_deposit_still_counts_it() -> None:
    found = _example()
    found.apply("move", {"direction": "north"}, _view("B1", True, ["east", "south", "west"]))
    text = found.render()
    assert "1  . @ . ? ? ?" in text and "Deposits seen: 1." in text


def test_the_orchestrators_view_and_other_scouts() -> None:
    text = _example().render({1: "A1", 2: "B2"}, here=False)
    lines = text.splitlines()
    assert lines[1] == "Field: 6 columns (A–F) × 6 rows (1–6)."
    assert lines[3] == "1  1 o . ? ? ?" and lines[4] == "2  . 2 . ? ? ?"
    assert lines[9] == "digits other scouts, o deposit, . seen without deposit, ? not seen yet."
