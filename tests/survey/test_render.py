"""`apl survey show` and the text and SVG pictures (specs/005 contracts/cli.md)."""

from pathlib import Path

import pytest

from apl.cli import main
from apl.survey import generate
from apl.survey.render_svg import svg
from apl.survey.render_text import render_text


def test_the_text_picture_of_an_open_field() -> None:
    field = generate("S1", 1000)
    text = render_text(field)
    lines = text.splitlines()
    assert lines[0] == (
        "Survey field S1, seed 1000: 6×6, 6 deposits; reference walk 36 steps (shortest); "
        "budget 108"
    )
    assert lines[1].split() == ["A", "B", "C", "D", "E", "F"]
    assert [line.split()[0] for line in lines[2::2][:6]] == ["1", "2", "3", "4", "5", "6"]
    assert "\n".join(lines[2:]).count("o") == 6 and "S" in lines[2]
    assert "|" not in text and "—" not in text


def test_walls_and_a_route() -> None:
    field = generate("S3", 1000)
    text = render_text(field, route=True)
    assert "|" in text or "—" in text
    assert "(a reference, not the shortest)" in text.splitlines()[0]
    assert " 1" in text  # the start is visit 1


def test_svg_has_every_cell_and_deposit() -> None:
    field = generate("S2", 1000)
    picture = svg(field)
    assert picture.startswith("<svg") and picture.count('class="cell"') == 100
    assert picture.count('class="deposit"') == 15


def test_cli_show(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    out = tmp_path / "field.html"
    assert main(["survey", "show", "--level", "S1", "--seed", "1000", "--html", str(out)]) == 0
    assert capsys.readouterr().out.startswith("Survey field S1, seed 1000")
    assert out.read_text().count("<svg") == 1
    assert main(["survey", "show", "--level", "S3", "--seed", "1000", "--route", "reference"]) == 0
    with pytest.raises(SystemExit):
        main(["survey", "show", "--level", "L1", "--seed", "1000"])
