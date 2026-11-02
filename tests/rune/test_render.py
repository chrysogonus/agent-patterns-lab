"""`apl rune show` and the text and SVG pictures (specs/010 contracts/cli.md)."""

from pathlib import Path

import pytest

from apl.cli import main
from apl.rune import generate
from apl.rune.model import cell_name
from apl.rune.render_svg import svg
from apl.rune.render_text import render_text
from apl.rune.rules import describe, reference_path

LETTER = {"red": "r", "blue": "b", "green": "g", "yellow": "y"}


def test_the_text_of_a_floor() -> None:
    floor = generate("R1", 1000)
    lines = render_text(floor).splitlines()
    assert lines[0] == (
        f"Rune floor R1, seed 1000: 7×5; rule: {describe(floor.rule)}; "
        f"reference {floor.reference} steps (optimal); budget {floor.budget}"
    )
    assert lines[1] == "    A B C D E F G"
    for y in range(5):
        cells = []
        for x in range(7):
            if (x, y) == floor.start:
                cells.append("S")
            elif (x, y) == floor.goal:
                cells.append("*")
            else:
                cells.append(LETTER[floor.colors[(x, y)]])
        assert lines[2 + y] == f"  {y + 1} " + " ".join(cells)
    assert lines[7] == "legend: r red, b blue, g green, y yellow, S start, * goal"
    assert len(lines) == 8


def test_r0_lists_its_trap_cells() -> None:
    floor = generate("R0", 1000)
    lines = render_text(floor).splitlines()
    assert lines[-1] == "traps: " + ", ".join(cell_name(c) for c in sorted(floor.rule.traps))
    assert 'id="truth-traps"' in svg(floor, animated=True)


def test_the_route_line() -> None:
    floor = generate("R3", 1000)
    lines = render_text(floor, route=True).splitlines()
    path = reference_path(floor)
    assert path is not None
    names = " → ".join(cell_name(c) for c in path)
    assert lines[-1] == f"reference: {names} ({floor.reference} moves)"
    assert lines[1] == "    A B C D E F G H I"


def test_svg_has_a_tile_per_cell() -> None:
    floor = generate("R2", 1000)
    picture = svg(floor)
    assert picture.startswith("<svg") and picture.count('data-cell="') == 9 * 7
    assert 'class="reference"' in picture and 'class="rule"' in picture
    animated = svg(floor, animated=True)
    for ident in ('id="trails"', 'id="traps"', 'id="agent"', 'id="reference"', 'id="rule"'):
        assert ident in animated


def test_cli_show(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    out = tmp_path / "floor.html"
    assert main(["rune", "show", "--level", "R1", "--seed", "1000", "--html", str(out)]) == 0
    assert capsys.readouterr().out.startswith("Rune floor R1, seed 1000")
    assert out.read_text().count("<svg") == 1
    assert main(["rune", "show", "--level", "R0", "--seed", "2000", "--route", "reference"]) == 0
    assert capsys.readouterr().out.splitlines()[-1].startswith("reference: A3 → ")
    with pytest.raises(SystemExit):
        main(["rune", "show", "--level", "T1", "--seed", "1000"])
