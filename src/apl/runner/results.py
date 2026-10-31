"""Episode rows and the settings record, written and read back (contracts/results.md)."""

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from apl.dungeon.env import Episode, Outcome
from apl.dungeon.results import EndReason
from apl.runner.meter import Meter
from apl.runner.spec import SEED_SETS, EpisodeKey


@dataclass(frozen=True, slots=True)
class EpisodeRow:
    run_id: str
    arch: str
    level: str
    seed: int
    seed_set: str
    repeat: int
    status: str  # "completed", or "error" for an infrastructure error (not scored)
    success: bool | None
    end_reason: str | None
    steps: int | None
    optimal_steps: int
    budget: int
    efficiency: float | None  # optimal_steps / steps on success
    invalid_actions: int | None
    budget_hit: bool | None
    token_cap_hit: bool | None
    output_limit_hits: int | None  # None in rows written before it was counted
    llm_calls: int
    tool_calls: int
    input_tokens: int | None  # None when the provider did not report usage
    output_tokens: int | None
    latency_s: float
    arch_error: str | None
    error: str | None
    scouts: int | None  # scouts that made a tool call (specs/004); None for errors and older rows
    orchestrator_calls: int | None  # model calls with the role "orchestrator"; None in older rows

    @classmethod
    def completed(
        cls,
        key: EpisodeKey,
        run_id: str,
        seed_set: str,
        outcome: Outcome,
        meter: Meter,
        latency_s: float,
        arch_error: str | None,
    ) -> "EpisodeRow":
        return cls(
            **_identity(key, run_id, seed_set),
            status="completed",
            success=outcome.success,
            end_reason=str(outcome.end_reason),
            steps=outcome.steps,
            optimal_steps=outcome.optimal_steps,
            budget=outcome.budget,
            efficiency=round(outcome.optimal_steps / outcome.steps, 3) if outcome.success else None,
            invalid_actions=outcome.invalid_actions,
            budget_hit=outcome.budget_hit,
            token_cap_hit=meter.token_cap_hit,
            output_limit_hits=meter.output_limit_hits,
            tool_calls=len(outcome.log),
            latency_s=round(latency_s, 1),
            arch_error=arch_error,
            error=None,
            llm_calls=meter.llm_calls,
            input_tokens=_tokens(meter, meter.input_tokens),
            output_tokens=_tokens(meter, meter.output_tokens),
            scouts=outcome.scouts,
            orchestrator_calls=meter.orchestrator_calls,
        )

    @classmethod
    def failed(
        cls,
        key: EpisodeKey,
        run_id: str,
        seed_set: str,
        episode: Episode,
        meter: Meter,
        latency_s: float,
        error: str,
    ) -> "EpisodeRow":
        return cls(
            **_identity(key, run_id, seed_set),
            status="error",
            success=None,
            end_reason=None,
            steps=None,
            optimal_steps=episode.dungeon.solution.length,
            budget=episode.dungeon.budget,
            efficiency=None,
            invalid_actions=None,
            budget_hit=None,
            token_cap_hit=None,
            output_limit_hits=meter.output_limit_hits,
            tool_calls=len(episode.log),
            latency_s=round(latency_s, 1),
            arch_error=None,
            error=error,
            llm_calls=meter.llm_calls,
            input_tokens=_tokens(meter, meter.input_tokens),
            output_tokens=_tokens(meter, meter.output_tokens),
            scouts=None,
            orchestrator_calls=meter.orchestrator_calls,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def parse(cls, data: object) -> "EpisodeRow":
        """A row read back from disk; `ValueError` naming the first bad field."""
        if not isinstance(data, dict):
            raise ValueError(f"a row must be an object, got {data!r}")
        data = {"output_limit_hits": None, "scouts": None, "orchestrator_calls": None, **data}
        names = [f.name for f in fields(cls)]
        odd = sorted(set(names) ^ set(data))
        if odd:
            name = odd[0]
            raise ValueError(f"field {name!r} is {'missing' if name in names else 'unexpected'}")
        for f in fields(cls):
            value, kind = data[f.name], _ROW_TYPES[f.name]
            if value is None and f.name in _NULLABLE:
                continue
            # bool is an int in Python, so check it explicitly; ints are fine for floats.
            ok = (
                isinstance(value, bool)
                if kind is bool
                else (isinstance(value, kind) and not isinstance(value, bool))
            )
            if not ok:
                expected = kind.__name__ if isinstance(kind, type) else "a number"
                raise ValueError(f"field {f.name!r} must be {expected}, got {value!r}")
        for name, allowed in _ALLOWED.items():
            if data[name] is not None and data[name] not in allowed:
                raise ValueError(f"field {name!r} must be one of {sorted(allowed)}")
        return cls(**data)


_ROW_TYPES: dict[str, type | tuple[type, ...]] = {
    f: int for f in ("seed", "repeat", "steps", "optimal_steps", "budget", "invalid_actions")
}
_ROW_TYPES.update(
    {f: str for f in ("run_id", "arch", "level", "seed_set", "status", "end_reason")},
    success=bool,
    budget_hit=bool,
    token_cap_hit=bool,
    efficiency=(int, float),
    latency_s=(int, float),
    llm_calls=int,
    output_limit_hits=int,
    tool_calls=int,
    input_tokens=int,
    output_tokens=int,
    arch_error=str,
    error=str,
    scouts=int,
    orchestrator_calls=int,
)
_NULLABLE = {
    "success", "end_reason", "steps", "efficiency", "invalid_actions", "budget_hit",
    "token_cap_hit", "output_limit_hits", "input_tokens", "output_tokens", "arch_error", "error",
    "scouts", "orchestrator_calls",
}  # fmt: skip
_ALLOWED: dict[str, set[str]] = {
    "status": {"completed", "error"},
    "end_reason": {str(r) for r in EndReason},
    "seed_set": set(SEED_SETS),
}


def _identity(key: EpisodeKey, run_id: str, seed_set: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "arch": key.arch,
        "level": key.level,
        "seed": key.seed,
        "seed_set": seed_set,
        "repeat": key.repeat,
    }


def _tokens(meter: Meter, count: int) -> int | None:
    return None if meter.usage_missing else count


@dataclass(frozen=True, slots=True)
class RunRecord:
    """run.json: everything needed to understand and compare a run later."""

    run_id: str
    started: str
    ended: str | None
    completed: bool
    architectures: tuple[str, ...]
    levels: tuple[str, ...]
    seed_set: str
    seeds: tuple[int, ...]
    repeats: int
    settings: dict[str, Any]
    code: dict[str, Any]
    versions: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {
            "architectures": list(self.architectures),
            "levels": list(self.levels),
            "seeds": list(self.seeds),
        }

    @classmethod
    def parse(cls, data: object) -> "RunRecord":
        if not isinstance(data, dict):
            raise ValueError("run.json must hold an object")
        names = [f.name for f in fields(cls)]
        for name in names:
            if name not in data:
                raise ValueError(f"run.json: field {name!r} is missing")
        try:
            return cls(
                **{n: data[n] for n in names}
                | {
                    "architectures": tuple(data["architectures"]),
                    "levels": tuple(data["levels"]),
                    "seeds": tuple(data["seeds"]),
                }
            )
        except TypeError as error:
            raise ValueError(f"run.json: {error}") from None


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def append_row(path: Path, row: EpisodeRow) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row.to_dict()) + "\n")
        file.flush()
