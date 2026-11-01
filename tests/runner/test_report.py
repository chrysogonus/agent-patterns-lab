"""Reports from hand-written runs, every figure checked by hand (User Story 3, SC-005, SC-006)."""

import json
from pathlib import Path
from typing import Any

import pytest

from apl.runner.report import check_compatible, load_run, render
from apl.runner.settings import Settings

SETTINGS = Settings().record()


def _row(seed: int, repeat: int, steps: int | None, **kw: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "run_id": kw.pop("run_id", "run-a"), "arch": kw.pop("arch", "react"),
        "level": kw.pop("level", "L1"), "seed": seed, "seed_set": "dev", "repeat": repeat,
        "status": "completed", "success": True, "end_reason": "exit", "steps": steps,
        "optimal_steps": 8, "budget": 24, "efficiency": None, "invalid_actions": 0,
        "budget_hit": False, "token_cap_hit": False, "output_limit_hits": 0, "llm_calls": 1,
        "tool_calls": steps or 0,
        "input_tokens": 0, "output_tokens": 0, "latency_s": 1.0, "arch_error": None,
        "error": None,
    }  # fmt: skip
    row.update(kw)
    if row["success"] and steps:
        row["efficiency"] = round(row["optimal_steps"] / steps, 3)
    return row


def _write(path: Path, rows: list[dict[str, Any]], **record: Any) -> Path:
    path.mkdir(parents=True)
    data = {
        "run_id": path.name, "started": "2026-10-30T15:12:00+01:00",
        "ended": "2026-10-30T15:20:00+01:00", "completed": True, "architectures": ["react"],
        "levels": ["L1", "L2"], "seed_set": "dev", "seeds": [1000, 1001], "repeats": 3,
        "settings": SETTINGS, "code": {"commit": None, "dirty": None}, "versions": {},
    }  # fmt: skip
    data.update(record)
    (path / "run.json").write_text(json.dumps(data))
    lines = [json.dumps({**r, "run_id": path.name}) for r in rows]
    (path / "episodes.jsonl").write_text("".join(line + "\n" for line in lines))
    return path


def _bad(**kw: Any) -> dict[str, Any]:
    return {"success": False, "end_reason": kw.pop("end_reason", "stopped"), **kw}


Tokens = tuple[int, int] | None


def _l1(seed: int, repeat: int, steps: int, invalid: int, calls: int, tokens: Tokens,
        latency: float, **kw: Any) -> dict[str, Any]:  # fmt: skip
    inp, out = tokens or (None, None)
    return _row(seed, repeat, steps, invalid_actions=invalid, llm_calls=calls, input_tokens=inp,
                output_tokens=out, latency_s=latency, **kw)  # fmt: skip


ROWS_A = [
    # L1: seed, repeat, steps, invalid, calls, (input, output) tokens, latency
    _l1(1000, 1, 10, 1, 11, (1000, 100), 2.0),
    _l1(1001, 1, 8, 0, 9, (800, 80), 1.0),
    _l1(1000, 2, 24, 5, 24, (3000, 300), 4.0, **_bad(end_reason="budget"), budget_hit=True),
    _l1(1001, 2, 16, 2, 17, None, 3.0),
    _l1(1000, 3, 3, 0, 2, (700000, 10), 5.0, **_bad(), token_cap_hit=True, output_limit_hits=2),
    _l1(1001, 3, 10, 1, 11, (1100, 110), 2.0),
    # L2: one completed episode and one infrastructure error
    _l1(1000, 1, 20, 3, 21, (5000, 500), 10.0, level="L2", optimal_steps=10),
    _row(
        1001,
        1,
        None,
        level="L2",
        status="error",
        success=None,
        end_reason=None,
        invalid_actions=None,
        budget_hit=None,
        token_cap_hit=None,
        llm_calls=3,
        error="RateLimitError: slow down",
    ),  # fmt: skip
]


def test_group_statistics(tmp_path: Path) -> None:
    report = render([load_run(_write(tmp_path / "run-a", ROWS_A))])
    # L1, 6 completed episodes:
    #   success 4/6 = 67%; efficiencies 0.8, 1.0, 0.5, 0.8 -> median 0.80
    #   invalid (1+0+5+2+0+1)/6 = 1.5; budget hit 1/6 = 17%; token cap 1/6 = 17%
    #   output limit hit in 1 of 6 episodes = 17%
    #   calls 2, 9, 11, 11, 17, 24 -> 11; input 800, 1000, 1100, 3000, 700000 -> 1,100
    #   output 10, 80, 100, 110, 300 -> 100; latency 1, 2, 2, 3, 4, 5 -> 2.5s
    assert (
        "| react | L1 | 6 | 67% | 0.80 | 1.5 | 17% | 17% | 17% | 11 | 1,100 | 100 | 2.5s |"
        in report
    )
    # L2: the error row is not scored, so 1 episode: 20 steps for optimal 10 -> 0.50
    assert (
        "| react | L2 | 1 | 100% | 0.50 | 3.0 | 0% | 0% | 0% | 21 | 5,000 | 500 | 10.0s |" in report
    )


def test_spread_across_repeats(tmp_path: Path) -> None:
    report = render([load_run(_write(tmp_path / "run-a", ROWS_A))])
    # L1 per repeat: r1 2/2, median(0.8, 1.0) = 0.9; r2 1/2, 0.5; r3 1/2, 0.8
    assert "| react | L1 | 50%–100% | 0.50–0.90 |" in report
    assert "| react | L2 | 100%–100% | 0.50–0.50 |" in report  # only r1 has a completed row


def test_errors_and_notes(tmp_path: Path) -> None:
    report = render([load_run(_write(tmp_path / "run-a", ROWS_A))])
    assert "## Infrastructure errors (not scored)" in report
    assert "| react | L2 | 1001 | 1 | RateLimitError: slow down |" in report
    assert "1 episode has no token data." in report
    assert "incomplete" not in report


def test_headers(tmp_path: Path) -> None:
    dev = render([load_run(_write(tmp_path / "dev", ROWS_A[:2]))])
    assert "> Development result (dev seeds). Must not be reported." in dev
    assert dev.startswith("# Report: react\n")
    assert "## Spread across repeats" in dev and "## Infrastructure errors" not in dev
    test_rows = [{**r, "seed_set": "test"} for r in ROWS_A[:2]]
    test = render([load_run(_write(tmp_path / "test", test_rows, seed_set="test"))])
    assert "> Result on test seeds." in test and "Must not be reported" not in test


def test_single_repeat_has_no_spread_and_empty_medians(tmp_path: Path) -> None:
    rows = [_row(1000, 1, 5, **_bad(), input_tokens=None, output_tokens=None)]
    report = render([load_run(_write(tmp_path / "one", rows, repeats=1, completed=False))])
    assert "## Spread across repeats" not in report
    assert "| react | L1 | 1 | 0% | — | 0.0 | 0% | 0% | 0% | 1 | — | — | 1.0s |" in report
    assert "Run one is incomplete." in report


def test_header_shows_the_model_limits(tmp_path: Path) -> None:
    report = render([load_run(_write(tmp_path / "run-a", ROWS_A[:1]))])
    assert "· context 16,384 · max output 8,192 ·" in report


def test_medians_are_whole_numbers(tmp_path: Path) -> None:
    rows = [_l1(1000, 1, 8, 0, 3, (1000, 11), 1.0), _l1(1001, 1, 8, 0, 4, (1003, 12), 1.0)]
    report = render([load_run(_write(tmp_path / "r", rows, repeats=1))])
    assert "| 4 | 1,002 | 12 |" in report  # 3.5, 1001.5 and 11.5, rounded half to even


def test_old_rows_without_the_output_limit_count(tmp_path: Path) -> None:
    rows = [
        {k: v for k, v in _l1(1000, 1, 8, 0, 3, (10, 1), 1.0).items() if k != "output_limit_hits"}
    ]
    report = render([load_run(_write(tmp_path / "old", rows, repeats=1))])
    assert "| react | L1 | 1 | 100% | 1.00 | 0.0 | 0% | 0% | — | 3 |" in report


def test_two_compatible_runs_share_a_table(tmp_path: Path) -> None:
    a = load_run(_write(tmp_path / "a", ROWS_A[:2]))
    b_rows = [{**r, "arch": "mapstate"} for r in ROWS_A[:2]]
    b = load_run(_write(tmp_path / "b", b_rows, architectures=["mapstate"], seeds=[1000]))
    report = render([a, b])
    assert report.startswith("# Report: mapstate, react\n")
    assert "| mapstate | L1 |" in report and "| react | L1 |" in report
    assert "did not all use the same seeds" in report


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model", "openai:gpt-6-sol"),
        ("temperature", 0.0),
        ("reasoning_effort", "none"),
        ("token_cap", 1000),
        ("num_ctx", 8192),
        ("max_output_tokens", 512),
        ("prompt_fingerprint", "000000000000"),
    ],
)
def test_incompatible_runs_are_refused(tmp_path: Path, field: str, value: object) -> None:
    a = load_run(_write(tmp_path / "a", ROWS_A[:1]))
    b = load_run(_write(tmp_path / "b", ROWS_A[:1], settings={**SETTINGS, field: value}))
    with pytest.raises(ValueError, match=f"cannot combine runs: {field} differs"):
        check_compatible([a, b])


def test_different_seed_sets_are_refused(tmp_path: Path) -> None:
    a = load_run(_write(tmp_path / "a", ROWS_A[:1]))
    test_rows = [{**ROWS_A[0], "seed_set": "test"}]
    b = load_run(_write(tmp_path / "b", test_rows, seed_set="test"))
    with pytest.raises(ValueError, match="seed_set differs"):
        render([a, b])


def test_bad_folders(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no run.json"):
        load_run(tmp_path)
    path = _write(tmp_path / "bad", ROWS_A[:2])
    with (path / "episodes.jsonl").open("a") as file:
        file.write('{"steps": 1}\n')
    with pytest.raises(ValueError, match=r"episodes.jsonl:3: field"):
        load_run(path)


def _survey(arch: str, seed: int, repeat: int, submitted: int | None, **kw: Any) -> dict[str, Any]:
    right = submitted == 15
    return _row(
        seed, repeat, kw.pop("steps", 100), arch=arch, level="S2", problem="survey",
        success=right, end_reason="submitted" if submitted is not None else "budget",
        optimal_steps=100, budget=300, submitted_total=submitted, true_total=15,
        cells_seen=kw.pop("seen", 100), cells=100, parallel_turns=kw.pop("turns", 100),
        reference_is_optimal=True, input_tokens=900, output_tokens=100, **kw,
    )  # fmt: skip


def test_the_survey_report(tmp_path: Path) -> None:
    rows = [
        _survey("react", 1000, 1, 15), _survey("react", 1000, 2, 12, seen=80),
        _survey("react", 1000, 3, 10, seen=70, steps=140, turns=140),
        _survey("fanout", 1000, 1, 15, steps=110, turns=30),
        _survey("fanout", 1000, 2, 15, steps=120, turns=32),
        _survey("fanout", 1000, 3, 14, steps=100, turns=28),
    ]  # fmt: skip
    path = _write(
        tmp_path / "run-s", rows, problem="survey", architectures=["react", "fanout"],
        levels=["S2"], seeds=[1000],
    )  # fmt: skip
    text = render([load_run(path)])
    assert text.startswith("# Report: fanout, react on the survey field\n")
    assert (
        "| Arch | Level | Episodes | Right | Off by (median) | Seen (median) | Steps (median) "
        "| Turns (median) | Tokens (median) | Latency (median) |"
    ) in text
    # react: right 1 of 3; off by 3 and 5 -> median 4; seen 100%, 80%, 70% -> 80%.
    assert "| react | S2 | 3 | 33% | 4 | 80% | 100 | 100 | 1,000 | 1.0s |" in text
    assert "| fanout | S2 | 3 | 67% | 1 | 100% | 110 | 30 | 1,000 | 1.0s |" in text
    assert "| react | S2 | 0%–100% | 100–140 | 100–140 |" in text
    # The comparison adds parallel turns; fanout's reference is mapstate, absent here.
    assert "| Δ right | Δ efficiency | Δ turns | Reference |" in text
    assert (
        "| fanout | 67% | 0.87 | 110 | 30 | 1,000 | — / — | 1.0s | — | — | — | — | mapstate |"
        in text
    )


def test_dungeon_and_survey_runs_are_not_combined(tmp_path: Path) -> None:
    dungeon = _write(tmp_path / "run-d", [_row(1000, 1, 8)])
    survey = _write(tmp_path / "run-s", [_survey("react", 1000, 1, 15)], problem="survey")
    with pytest.raises(
        ValueError,
        match=r"^these runs are on different problems \(dungeon, survey\); report them separately$",
    ):
        check_compatible([load_run(dungeon), load_run(survey)])
