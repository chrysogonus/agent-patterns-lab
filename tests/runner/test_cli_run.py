"""`apl run` and `apl report` (contracts/cli.md)."""

from pathlib import Path

import pytest

from apl.cli import main
from apl.runner import registry

DRY = ["run", "--arch", "react", "--level", "all", "--seeds", "dev", "--limit", "2"]


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return work


def test_dry_run_prints_the_plan_and_writes_nothing(
    workdir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(DRY) == 0
    out = capsys.readouterr().out
    for line in [
        "episodes       6",
        "model          vllm:qwen3.5-9b",
        "context        from the server (read at --execute)",
        "max output     8,192 tokens per call",
        "temperature    provider default",
        "reasoning      provider default",
        "token cap      2,000,000 per episode",
        "model calls    450",
        "tokens         12,000,000",
        "cost           no estimate (set APL_PRICE_INPUT and APL_PRICE_OUTPUT)",
        "seeds          dev: 1000, 1001 (2 of 10)  -> development only, must not be reported",
        "Run with --execute to start it (a paid provider then costs money).",
    ]:
        assert line in out
    assert list(workdir.iterdir()) == []  # SC-001; the network guard would have raised


def test_dry_run_for_ollama_shows_its_context(
    workdir: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APL_MODEL", "ollama:qwen3:8b")
    assert main(DRY) == 0
    out = capsys.readouterr().out
    assert "context        16,384 tokens" in out and "max output     4,096 tokens per call" in out


def test_dry_run_with_prices(
    workdir: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APL_PRICE_INPUT", "0.10")
    monkeypatch.setenv("APL_PRICE_OUTPUT", "0.50")
    assert main(DRY) == 0
    assert "cost           $6.00 (at $0.10 / $0.50 per 1M tokens)" in capsys.readouterr().out


def test_test_seeds_are_for_reporting(workdir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--arch", "react", "--level", "L1", "--seeds", "test"]) == 0
    assert "(20 of 20)  -> for reporting" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (
            ["--arch", "nope", "--level", "L1"],
            "registered: hybrid, mapstate, mapstate_routes, react",
        ),
        (["--arch", "react", "--level", "L9"], "unknown level 'L9' (levels: L1, L2, L3, all)"),
        (["--arch", "react", "--level", "L1", "--only", "5"], "not in the dev seeds"),
        (["--arch", "react", "--level", "L1", "--only", "x"], "--only"),
    ],
)
def test_invalid_run_descriptions(
    workdir: Path, capsys: pytest.CaptureFixture[str], args: list[str], message: str
) -> None:
    assert main(["run", "--seeds", "dev", *args]) == 2
    assert message in capsys.readouterr().err


def test_invalid_setting(
    workdir: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APL_TOKEN_CAP", "lots")
    assert main(DRY) == 2
    assert "APL_TOKEN_CAP" in capsys.readouterr().err


def test_unwritten_architecture_is_planned(
    workdir: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(registry, "is_written", lambda name: False)
    assert main(DRY) == 0
    assert "architectures  react (not written yet)" in capsys.readouterr().out


EXECUTE = ["run", "--arch", "loop", "--level", "L1", "--seeds", "dev", "--limit", "2", "--execute"]


@pytest.fixture
def scripted_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Registers the test-only loop architecture and swaps in the scripted model."""
    from apl.runner import run, vllm
    from tests.runner.scripted import scripted_factory, text_answer

    monkeypatch.setitem(registry.ARCHITECTURES, "loop", "tests.runner.loop_arch")
    monkeypatch.setattr(run, "default_model_factory", scripted_factory(text_answer()))
    monkeypatch.setattr(vllm, "with_server_context", lambda settings: settings)


def test_execute_needs_the_api_key(
    workdir: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY")
    monkeypatch.setenv("APL_MODEL", "openai:gpt-6-luna")
    assert main([*DRY, "--execute"]) == 2
    assert "OPENAI_API_KEY is not set (needed for openai:gpt-6-luna)" in capsys.readouterr().err
    assert list(workdir.iterdir()) == []


def test_execute_refuses_an_unwritten_architecture(
    workdir: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(registry, "is_written", lambda name: False)
    assert main([*DRY, "--execute"]) == 2
    assert "architecture react is not written yet" in capsys.readouterr().err
    assert list(workdir.iterdir()) == []


def test_execute_prints_progress(
    workdir: Path, capsys: pytest.CaptureFixture[str], scripted_loop: None
) -> None:
    assert main(EXECUTE) == 0
    out = capsys.readouterr().out
    (run_dir,) = (workdir / "results").iterdir()
    assert "[1/2] loop L1 1000 r1  stopped  steps 0/" in out
    assert "[2/2] loop L1 1001 r1  stopped  steps 0/" in out
    assert "calls 1  tokens 25  " in out
    assert f"results/{run_dir.name}" in out


def test_execute_ends_with_the_report(
    workdir: Path, capsys: pytest.CaptureFixture[str], scripted_loop: None
) -> None:
    assert main(EXECUTE) == 0
    (run_dir,) = (workdir / "results").iterdir()
    report = (run_dir / "report.md").read_text()
    assert "| loop | L1 | 2 | 0% |" in report and report in capsys.readouterr().out


def test_report_command(
    workdir: Path, capsys: pytest.CaptureFixture[str], scripted_loop: None
) -> None:
    main(EXECUTE)
    main([*EXECUTE[:-2], "1", "--execute"])  # a second run with one seed
    first, second = sorted((workdir / "results").iterdir())
    (first / "report.md").unlink()
    capsys.readouterr()
    assert main(["report", str(first)]) == 0
    assert (first / "report.md").read_text() in capsys.readouterr().out
    assert main(["report", str(first), str(second)]) == 0
    combined = list((workdir / "results").glob("report-*.md"))
    assert len(combined) == 1 and "did not all use the same seeds" in combined[0].read_text()


def test_report_refuses_bad_input(
    workdir: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    scripted_loop: None,
) -> None:
    assert main(["report", str(workdir)]) == 2
    assert "no run.json" in capsys.readouterr().err
    main(EXECUTE)
    monkeypatch.setenv("APL_TOKEN_CAP", "1000")
    main(EXECUTE)
    first, second = sorted((workdir / "results").iterdir())
    capsys.readouterr()
    assert main(["report", str(first), str(second)]) == 2
    assert (
        "apl: cannot combine runs: token_cap differs (2000000 vs 1000)" in capsys.readouterr().err
    )


def test_dungeon_show_does_not_load_langchain() -> None:
    import subprocess
    import sys

    code = "import apl.cli, sys; sys.exit('langchain' in sys.modules or 'langgraph' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
