"""What `apl run` was asked to do, and its dry-run plan (data-model "RunSpec", research R10)."""

from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass

from apl import problems
from apl.dungeon import DEV_SEEDS, TEST_SEEDS
from apl.runner.registry import ARCHITECTURES, SUPPORTS, plays, refusal
from apl.runner.settings import Settings

SEED_SETS = {"dev": DEV_SEEDS, "test": TEST_SEEDS}  # the dungeon's; each problem has its own


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
    problem: str = problems.DEFAULT

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
        problem: str | None = None,
        supports: Mapping[str, Collection[str]] = SUPPORTS,
    ) -> "RunSpec":
        chosen = problems.get(problem)
        for name in architectures:
            if name not in known:
                raise ValueError(
                    f"unknown architecture {name!r} (registered: {', '.join(sorted(known))})"
                )
        for name in architectures:
            if not plays(name, chosen.name, supports):
                raise ValueError(refusal(name, chosen.name, supports))
        if list(levels) == ["all"]:
            levels = sorted(chosen.levels)
        for level in levels:
            if level not in chosen.levels:
                names = ", ".join(sorted(chosen.levels))
                raise ValueError(f"unknown level {level!r} (levels: {names}, all)")
        if seed_set not in chosen.seed_sets:
            raise ValueError(f"unknown seed set {seed_set!r}: use dev or test")
        available = tuple(chosen.seed_sets[seed_set])
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
            chosen.name,
        )

    def episodes(self) -> Iterator[EpisodeKey]:
        # Every architecture plays a dungeon before the next one, so a cut-off run stays paired.
        for level in self.levels:
            for seed in self.seeds:
                for repeat in range(1, self.repeats + 1):
                    for arch in self.architectures:
                        yield EpisodeKey(arch, level, seed, repeat)

    def upper_bounds(self, settings: Settings) -> Bounds:
        return upper_bounds(list(self.episodes()), settings, self.problem)


def upper_bounds(
    keys: Sequence[EpisodeKey], settings: Settings, problem: str = problems.DEFAULT
) -> Bounds:
    """Tokens and cost are hard bounds (the token cap); calls assume one per step plus an answer."""
    generate = problems.get(problem).generate
    budgets = {(k.level, k.seed): generate(k.level, k.seed).budget for k in keys}
    tokens = len(keys) * settings.token_cap
    cost = None
    if settings.price_input is not None and settings.price_output is not None:
        cost = tokens * max(settings.price_input, settings.price_output) / 1_000_000
    return Bounds(sum(budgets[k.level, k.seed] + 1 for k in keys), tokens, cost)


def code_line(code: Mapping[str, object]) -> str:
    """The commit for a dry run, and whether the run could be continued (specs/004 R12)."""
    commit = code.get("commit")
    short = str(commit)[:7] if commit else "unknown"
    return short + (
        " (uncommitted changes: this run cannot be continued)" if code.get("dirty") else ""
    )


def format_limits(bounds: Bounds, settings: Settings) -> list[str]:
    if bounds.cost is None:
        cost = "no estimate (set APL_PRICE_INPUT and APL_PRICE_OUTPUT)"
    else:
        cost = (
            f"${bounds.cost:,.2f} (at ${settings.price_input:.2f} / "
            f"${settings.price_output:.2f} per 1M tokens)"
        )
    # Calls are an estimate: A6's re-asks and the orchestrators' calls are not tied to steps.
    limits = [
        ("model calls (est.)", f"{bounds.calls:,}"),
        ("tokens", f"{bounds.tokens:,}"),
        ("cost", cost),
    ]
    return ["At most"] + [f"  {k:<15}{v}" if len(k) < 15 else f"  {k}  {v}" for k, v in limits]


def format_plan(
    spec: RunSpec,
    settings: Settings,
    written: Mapping[str, bool],
    code: Mapping[str, object] | None = None,
) -> str:
    record = settings.record(spec.problem)
    bounds = spec.upper_bounds(settings)
    meaning = (
        "for reporting" if spec.seed_set == "test" else "development only, must not be reported"
    )
    total = len(problems.get(spec.problem).seed_sets[spec.seed_set])
    seeds = f"{spec.seed_set}: {', '.join(map(str, spec.seeds))} ({len(spec.seeds)} of {total})"
    archs = [a if written.get(a, True) else f"{a} (not written yet)" for a in spec.architectures]
    rows = [
        ("architectures", ", ".join(archs)),
        *([("problem", spec.problem)] if spec.problem != problems.DEFAULT else []),
        ("levels", ", ".join(spec.levels)),
        ("seeds", f"{seeds}  -> {meaning}"),
        ("repeats", str(spec.repeats)),
        ("episodes", str(len(list(spec.episodes())))),
        ("model", settings.model),
        ("temperature", str(record["temperature"])),
        ("reasoning", str(record["reasoning_effort"])),
        *(
            [("context", "from the server (read at --execute)")]
            if settings.model.startswith("vllm:")
            else [("context", f"{settings.num_ctx:,} tokens")]
            if record["num_ctx"]
            else []
        ),
        ("max output", f"{settings.max_output_tokens:,} tokens per call"),
        ("token cap", f"{settings.token_cap:,} per episode"),
        ("prompt", str(record["prompt_fingerprint"])),
        *([("code", code_line(code))] if code is not None else []),
    ]
    lines = ["Plan (dry run, nothing is sent or written)"]
    lines += [f"  {k:<15}{v}" for k, v in rows]
    lines += format_limits(bounds, settings)
    lines.append("Run with --execute to start it (a paid provider then costs money).")
    return "\n".join(lines)
