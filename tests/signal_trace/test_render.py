"""`apl signal show` and the text and SVG pictures (specs/009 contracts/cli.md)."""

import re
from pathlib import Path

import pytest

from apl.cli import main
from apl.signal_trace import DEV_SEEDS, TEST_SEEDS, generate
from apl.signal_trace.render_svg import CELL, MARGIN, svg
from apl.signal_trace.render_text import render_text
from apl.signal_trace.strategy import reference_run


def test_the_text_of_a_straight_pipe() -> None:
    pipe = generate("T1", 1000)
    lines = render_text(pipe).splitlines()
    assert lines[0] == (
        f"Signal trace T1, seed 1000: 16 segments, 1 run; broken segment {pipe.broken}; "
        "reference 5 steps (optimal); budget 16"
    )
    assert lines[1:] == ["  S → 1–16"]


def test_a_tree_prints_one_line_per_run_and_the_route() -> None:
    pipe = generate("T3", 1000)
    lines = render_text(pipe, route=True).splitlines()
    assert "(a reference)" in lines[0] and f"{len(pipe.runs)} runs" in lines[0]
    assert lines[1] == f"  S → 1–{pipe.runs[0].last}"
    assert lines[2] == f"  {pipe.runs[1].feeder} → {pipe.runs[1].first}–{pipe.runs[1].last}"
    probes, submitted = reference_run(pipe)
    said = ", ".join(f"{k} {'wet' if w else 'dry'}" for k, w in probes)
    assert lines[-1] == f"reference: {said} → submit {submitted}"
    assert len(lines) == 1 + len(pipe.runs) + 1


def test_svg_has_a_box_per_segment() -> None:
    pipe = generate("T3", 1000)
    picture = svg(pipe)
    assert picture.startswith("<svg") and picture.count('data-seg="') == 64
    assert picture.count("broken") == 1


def test_cli_show(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    out = tmp_path / "pipe.html"
    assert main(["signal", "show", "--level", "T1", "--seed", "1000", "--html", str(out)]) == 0
    assert capsys.readouterr().out.startswith("Signal trace T1, seed 1000")
    assert out.read_text().count("<svg") == 1
    assert main(["signal", "show", "--level", "T2", "--seed", "2000", "--route", "reference"]) == 0
    assert capsys.readouterr().out.splitlines()[-1].startswith("reference: 32 ")
    with pytest.raises(SystemExit):
        main(["signal", "show", "--level", "S1", "--seed", "1000"])


def _width(picture: str) -> int:
    match = re.search(r'viewBox="0 0 (\d+) \d+"', picture)
    assert match
    return int(match.group(1))


def test_a_long_pipe_is_drawn_wider() -> None:  # specs/013 research R8
    assert _width(svg(generate("T3", 1000))) == 2 * MARGIN + 64 + 8 * CELL == 300
    picture = svg(generate("T4", 1000))
    assert picture.count('data-seg="') == 256
    assert _width(picture) == 2 * MARGIN + 80 + 24 * CELL == 732


def test_t4_labels_fit_inside_the_picture() -> None:  # 12 px monospace, about 7.2 px a character
    for seed in [*DEV_SEEDS, *TEST_SEEDS]:
        picture = svg(generate("T4", seed))
        labels = re.findall(r'<text class="label[^"]*" x="(-?\d+)"[^>]*>([^<]+)</text>', picture)
        assert labels and any(text.startswith("from ") for _, text in labels)
        for x, text in labels:
            assert int(x) - len(text) * 7.2 >= MARGIN / 2, (seed, text)


def test_cli_show_t4(capsys: pytest.CaptureFixture[str]) -> None:
    pipe = generate("T4", 1000)
    assert main(["signal", "show", "--level", "T4", "--seed", "1000", "--route", "reference"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("Signal trace T4, seed 1000: 256 segments, 15 runs")
    assert len(lines) == 1 + len(pipe.runs) + 1 and lines[-1].startswith("reference: ")
    with pytest.raises(SystemExit) as raised:
        main(["signal", "show", "--level", "T9", "--seed", "1000"])
    assert raised.value.code == 2
