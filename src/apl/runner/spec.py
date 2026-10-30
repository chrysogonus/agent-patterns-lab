"""What `apl run` was asked to do, and its dry-run plan (data-model "RunSpec", research R10)."""

from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass

from apl.dungeon import DEV_SEEDS, LEVELS, TEST_SEEDS, generate
from apl.runner.registry import ARCHITECTURES
from apl.runner.settings import Settings

SEED_SETS = {"dev": DEV_SEEDS, "test": TEST_SEEDS}


@dataclass(frozen=True, slots=True)
class EpisodeKey:
    arch: str
    level: str
    seed: int
    repeat: int  # from 1

    @property
    def name(self) -> str:
        return f"{self.arch}-{self.level}-{self.seed}-r{self.repeat}"


@dataclass(frozen=True, slots=True)
class Bounds:
    calls: int
    tokens: int
    cost: float | None  # USD, only with prices


def _unique(kind: str, names: Sequence[str]) -> tuple[str, ...]:
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate {kind} in {', '.join(names)}")
    return tuple(names)


@dataclass(frozen=True, slots=True)
class RunSpec:
    architectures: tuple[str, ...]
    levels: tuple[str, ...]
    seed_set: str
    seeds: tuple[int, ...]
    repeats: int

    @classmethod
    def build(
        cls,
        architectures: Sequence[str],
        levels: Sequence[str],
        seed_set: str,
        limit: int | None = None,
        only: Sequence[int] | None = None,
        repeats: int = 1,
        known: Collection[str] = ARCHITECTURES,
    ) -> "RunSpec":
        for name in architectures:
            if name not in known:
                raise ValueError(
                    f"unknown architecture {name!r} (registered: {', '.join(sorted(known))})"
                )
        if list(levels) == ["all"]:
            levels = sorted(LEVELS)
        for level in levels:
            if level not in LEVELS:
                raise ValueError(f"unknown level {level!r} (levels: L1, L2, L3, all)")
        if seed_set not in SEED_SETS:
            raise ValueError(f"unknown seed set {seed_set!r}: use dev or test")
        available = tuple(SEED_SETS[seed_set])
        if limit is not None and only is not None:
            raise ValueError("use --limit or --only, not both")
        seeds = available
        if limit is not None:
            if not 1 <= limit <= len(available):
                raise ValueError(f"--limit must be between 1 and {len(available)}")
            seeds = available[:limit]
        if only is not None:
            missing = [s for s in only if s not in available]
            if missing:
                raise ValueError(f"seeds {missing} are not in the {seed_set} seeds")
            seeds = tuple(only)
        if repeats < 1:
            raise ValueError("--repeats must be at least 1")
        return cls(
            _unique("architectures", architectures),
            _unique("levels", levels),
            seed_set,
            seeds,
            repeats,
        )

    def episodes(self) -> Iterator[EpisodeKey]:
        for arch in self.architectures:
            for level in self.levels:
                for seed in self.seeds:
                    for repeat in range(1, self.repeats + 1):
                        yield EpisodeKey(arch, level, seed, repeat)

    def upper_bounds(self, settings: Settings) -> Bounds:
        """Real upper bounds: one model call per step plus a final answer; the token cap."""
        budgets = {(lv, s): generate(lv, s).budget for lv in self.levels for s in self.seeds}
        keys = list(self.episodes())
        tokens = len(keys) * settings.token_cap
        cost = None
        if settings.price_input is not None and settings.price_output is not None:
            cost = tokens * max(settings.price_input, settings.price_output) / 1_000_000
        return Bounds(sum(budgets[k.level, k.seed] + 1 for k in keys), tokens, cost)


def format_plan(spec: RunSpec, settings: Settings, written: Mapping[str, bool]) -> str:
    record = settings.record()
    bounds = spec.upper_bounds(settings)
    meaning = (
        "for reporting" if spec.seed_set == "test" else "development only, must not be reported"
    )
    total = len(SEED_SETS[spec.seed_set])
    seeds = f"{spec.seed_set}: {', '.join(map(str, spec.seeds))} ({len(spec.seeds)} of {total})"
    archs = [a if written.get(a, True) else f"{a} (not written yet)" for a in spec.architectures]
    if bounds.cost is None:
        cost = "no estimate (set APL_PRICE_INPUT and APL_PRICE_OUTPUT)"
    else:
        cost = (
            f"${bounds.cost:,.2f} (at ${settings.price_input:.2f} / "
            f"${settings.price_output:.2f} per 1M tokens)"
        )
    rows = [
        ("architectures", ", ".join(archs)),
        ("levels", ", ".join(spec.levels)),
        ("seeds", f"{seeds}  -> {meaning}"),
        ("repeats", str(spec.repeats)),
        ("episodes", str(len(list(spec.episodes())))),
        ("model", settings.model),
        ("temperature", str(record["temperature"])),
        ("reasoning", str(record["reasoning_effort"])),
        *([("context", f"{settings.num_ctx:,} tokens")] if record["num_ctx"] else []),
        ("token cap", f"{settings.token_cap:,} per episode"),
        ("prompt", str(record["prompt_fingerprint"])),
    ]
    limits = [
        ("model calls", f"{bounds.calls:,}"),
        ("tokens", f"{bounds.tokens:,}"),
        ("cost", cost),
    ]
    lines = ["Plan (dry run, nothing is sent or written)"]
    lines += [f"  {k:<15}{v}" for k, v in rows]
    lines += ["At most"] + [f"  {k:<15}{v}" for k, v in limits]
    lines.append("Run with --execute to start it (a paid provider then costs money).")
    return "\n".join(lines)
