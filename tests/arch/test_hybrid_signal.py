"""A6 on the signal trace: code lists the probes, the model picks one (specs/009 contracts)."""

import re

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.hybrid import MAX_MISSES, SIGNAL_HYBRID_INSTRUCTIONS
from apl.signal_trace import DEV_SEEDS, generate
from apl.signal_trace.prompt import BASE_PROMPT
from tests.arch.orchestrated import recording, text
from tests.arch.signal_play import play

OPTION = re.compile(r"^(\d+)\. (.*)$", re.MULTILINE)


def _options(messages: list[BaseMessage]) -> list[str]:
    return [m[2] for m in OPTION.finditer(text(messages).split("Options:\n", 1)[1])]


def _first() -> AIMessage:
    return AIMessage("1")


def test_the_first_options_split_the_pipe_most_evenly() -> None:
    seen: list[list[BaseMessage]] = []
    play("hybrid", "T2", 1000, recording(lambda m: _first(), seen))
    assert str(seen[0][0].content) == BASE_PROMPT + "\n\n" + SIGNAL_HYBRID_INSTRUCTIONS
    first = _options(seen[0])
    assert [int(o.split()[1].rstrip(":")) for o in first] == [32, 31, 33, 30, 34, 29, 35, 28]
    assert first[0] == "probe 32: leaves 32 if wet, 32 if dry"
    assert first[1] == "probe 31: leaves 33 if wet, 31 if dry"
    assert "Pipe: 64 segments." in text(seen[0])


def test_submissions_are_offered_near_the_end() -> None:
    seen: list[list[BaseMessage]] = []
    pipe = generate("T2", 1000)
    result = play("hybrid", "T2", 1000, recording(lambda m: _first(), seen))
    lists = [_options(m) for m in seen]
    assert all(not any(o.startswith("submit") for o in options) for options in lists[:4])
    near = [o for o in lists if any(x.startswith("submit") for x in o)]
    assert near and all(len([x for x in o if x.startswith("submit")]) <= 4 for o in near)
    assert lists[-1] == [f"submit {pipe.broken}"]
    assert result.row.success


def test_answering_1_finds_every_break_like_the_reference() -> None:
    for seed in DEV_SEEDS:
        pipe = generate("T2", seed)
        result = play("hybrid", "T2", seed, lambda m: _first())
        outcome = result.outcome
        assert result.row.success and outcome is not None, seed
        assert outcome.probes <= pipe.reference_probes and outcome.wasted_probes == 0


def test_answers_that_name_no_option_are_asked_again_then_end() -> None:
    seen: list[list[BaseMessage]] = []
    result = play("hybrid", "T1", 1000, recording(lambda m: AIMessage("the middle one"), seen))
    assert len(seen) == MAX_MISSES and result.row.steps == 0
    assert result.row.end_reason == "stopped"
    assert "named no option" in text(seen[1])
