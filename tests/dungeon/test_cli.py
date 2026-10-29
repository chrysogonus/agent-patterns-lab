"""`apl dungeon show` (contracts/cli.md)."""

import json
from pathlib import Path

import pytest

from apl.cli import main
from apl.dungeon import generate, start_episode


def test_show_prints_the_map(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["dungeon", "show", "--level", "L3", "--seed", "1000"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("+") and "S" in out and "E" in out


def test_show_with_solution(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["dungeon", "show", "--level", "L2", "--seed", "1000", "--route", "solution"]) == 0
    assert capsys.readouterr().out.rstrip().endswith("(exit)")


def test_show_with_route_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    actions = tmp_path / "actions.json"
    actions.write_text(json.dumps({"actions": [{"tool": "move", "args": ["up"]}]}))
    assert (
        main(["dungeon", "show", "--level", "L1", "--seed", "1000", "--route", str(actions)]) == 0
    )
    assert "invalid_direction" in capsys.readouterr().out

    episode = start_episode(generate("L1", 1000))
    episode.look()
    episode.stop()
    log = tmp_path / "log.json"
    log.write_text(json.dumps(episode.outcome().to_dict()))
    assert main(["dungeon", "show", "--level", "L1", "--seed", "1000", "--route", str(log)]) == 0
    assert "(stopped)" in capsys.readouterr().out


@pytest.mark.parametrize(
    "args",
    [
        ["dungeon", "show", "--level", "L9", "--seed", "1"],
        ["dungeon", "show", "--level", "L1", "--seed", "-1"],
        ["dungeon", "show", "--level", "L1", "--seed", "1", "--route", "/nonexistent.json"],
        ["dungeon"],
        [],
    ],
)
def test_invalid_arguments_exit_2(args: list[str]) -> None:
    try:
        code = main(args)
    except SystemExit as exit:
        code = int(exit.code or 0)
    assert code == 2


@pytest.mark.parametrize(
    "content",
    ["{not json", '{"log": [], "end_reason": []}', '{"actions": [{"tool": "move", "args": [1]}]}'],
)
def test_malformed_route_file_exits_2(
    tmp_path: Path, content: str, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(content)
    assert main(["dungeon", "show", "--level", "L1", "--seed", "1", "--route", str(bad)]) == 2
    assert capsys.readouterr().err.startswith("apl: ")


def test_show_writes_html(tmp_path: Path) -> None:
    still, animated = tmp_path / "still.html", tmp_path / "animated.html"
    base = ["dungeon", "show", "--level", "L2", "--seed", "1000"]
    assert main([*base, "--html", str(still)]) == 0
    assert main([*base, "--route", "solution", "--html", str(animated)]) == 0
    assert "<script" not in still.read_text() and 'id="apl-frames"' in animated.read_text()
    assert main([*base, "--html", str(tmp_path / "missing" / "x.html")]) == 2
