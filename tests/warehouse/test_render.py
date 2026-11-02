"""`apl warehouse show` and the text and SVG pictures (specs/012 contracts/cli.md)."""

from pathlib import Path

import pytest

from apl.cli import main
from apl.warehouse import generate
from apl.warehouse.render_svg import svg
from apl.warehouse.render_text import render_text
from tests.warehouse.floors import p2_floor


def test_the_text_of_the_hand_built_floor() -> None:
    assert render_text(p2_floor()).splitlines() == [
        "Warehouse custom, seed None: 3 packages; reference 46 steps (not optimal); budget 138",
        "   A B C D E F G H I",
        "1  . . . . 2 . . . .",
        "2  S # # # # # # # D",
        "3  . . . . . . . . .",
        "4  . # # # # # # # .",
        "5  . 1 . . . . 3 . .",
        "aisles: aisle 1 (row 1): 1 package; aisle 2 (row 3): none; aisle 3 (row 5): 2 packages",
    ]


def test_the_route_line() -> None:
    last = render_text(p2_floor(), route=True).splitlines()[-1]
    assert last.startswith("reference: move north, move east, ") and last.endswith(", drop")


def test_svg_has_rooms_and_packages() -> None:
    floor = generate("P3", 1000)
    picture = svg(floor)
    assert picture.startswith("<svg")
    assert picture.count('data-package="') == len(floor.packages)
    open_cells = sum(
        1 for y in range(floor.rows) for x in range(floor.columns) if floor.open((x, y))
    )
    assert picture.count('class="room"') == open_cells


def test_the_show_command(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["warehouse", "show", "--level", "P2", "--seed", "1000"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Warehouse P2, seed 1000: 3 packages; reference ")
    assert (
        main(["warehouse", "show", "--level", "P2", "--seed", "2000", "--route", "reference"]) == 0
    )
    assert capsys.readouterr().out.splitlines()[-1].startswith("reference: ")
    page = tmp_path / "floor.html"
    assert main(["warehouse", "show", "--level", "P1", "--seed", "1000", "--html", str(page)]) == 0
    assert "<svg" in page.read_text()
    with pytest.raises(SystemExit) as exit_info:
        main(["warehouse", "show", "--level", "P9", "--seed", "1000"])
    assert exit_info.value.code == 2
