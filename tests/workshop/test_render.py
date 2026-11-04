"""`apl workshop show` and the text and SVG pictures (specs/011 contracts/cli.md)."""

from pathlib import Path

import pytest

from apl.cli import main
from apl.workshop import DEV_SEEDS, TEST_SEEDS, generate
from apl.workshop.render_svg import BOX_W, GAP_X, layers, places, svg
from apl.workshop.render_text import render_text
from tests.workshop.lantern import lantern


def test_the_text_of_the_lantern() -> None:
    lines = render_text(lantern()).splitlines()
    assert lines == [
        "Workshop custom, seed None: goal lantern; reference 15 steps (optimal); budget 45",
        "stock: coal 1 (scarce), iron ore 2, resin 1, sand 2, seeds 1, wood 1",
        "  lantern: frame, lens, oil",
        "  frame: ! iron bar | * wood, resin",
        "  iron bar: coal, iron ore",
        "  lens: glass",
        "  glass: sand, coal",
        "  oil: seeds",
    ]


def test_the_route_line() -> None:
    lines = render_text(lantern(), route=True).splitlines()
    assert lines[-1].startswith("reference: inspect lantern, inspect frame, gather wood, ")
    assert lines[-1].endswith(", craft oil 1, craft lantern 1")


def test_svg_has_a_box_per_item() -> None:
    w = generate("W3", 1000)
    picture = svg(w)
    items = {*w.recipes, *w.stock}
    assert picture.startswith("<svg") and picture.count('data-item="') == len(items)
    assert ' w-ref" data-from=' in picture
    animated = svg(w, animated=True)
    assert 'id="badges"' in animated


def test_cli_show(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    out = tmp_path / "workshop.html"
    assert main(["workshop", "show", "--level", "W2", "--seed", "1000", "--html", str(out)]) == 0
    assert capsys.readouterr().out.startswith("Workshop W2, seed 1000: goal ")
    assert out.read_text().count("<svg") == 1
    assert (
        main(["workshop", "show", "--level", "W1", "--seed", "2000", "--route", "reference"]) == 0
    )
    assert capsys.readouterr().out.splitlines()[-1].startswith("reference: inspect ")
    with pytest.raises(SystemExit):
        main(["workshop", "show", "--level", "R1", "--seed", "1000"])


def test_w4_draws_every_item_once_without_overlap() -> None:  # specs/013 research R9
    for seed in [*DEV_SEEDS, *TEST_SEEDS]:
        w = generate("W4", seed)
        assert svg(w).count('data-item="') == len(w.recipes) + len(w.stock)
        assert max(len(row) for row in layers(w)) <= 7
        boxes = places(w)
        for row in layers(w):
            xs = sorted(boxes[item][0] for item in row)
            assert all(b - a >= BOX_W + GAP_X for a, b in zip(xs, xs[1:], strict=False))


def test_cli_show_w4(capsys: pytest.CaptureFixture[str]) -> None:
    w = generate("W4", 1000)
    assert (
        main(["workshop", "show", "--level", "W4", "--seed", "1000", "--route", "reference"]) == 0
    )
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith(f"Workshop W4, seed 1000: goal {w.goal}; reference {w.reference}")
    assert lines[1].count("(scarce)") == 3 and lines[-1].startswith("reference: ")
    with pytest.raises(SystemExit) as raised:
        main(["workshop", "show", "--level", "W9", "--seed", "1000"])
    assert raised.value.code == 2
