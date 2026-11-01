# Contract: Problems

Research R2, R3, R15. Runner side; architectures never import `apl.problems`.

## Registry

```python
# apl/problems.py
@dataclass(frozen=True, slots=True)
class Problem:
    name: str
    levels: Mapping[str, object]  # level name -> level
    dev_seeds: range
    test_seeds: range
    generate: Callable[[str, int], World]  # deterministic
    reference_steps: Callable[[World], int]
    start_episode: Callable[[World], EpisodeLike]
    build_kit: Callable[[EpisodeLike, BaseChatModel], Kit]
    prompt_fingerprint: Callable[[], str]


PROBLEMS: dict[str, Problem]  # "dungeon", "survey"
DEFAULT = "dungeon"


def get(
    name: str | None,
) -> Problem: ...  # None -> DEFAULT; unknown -> ValueError naming the problems
```

`World` has at least `budget: int`. `Problem.reference_steps(world)` gives the shortest solution
(the dungeon's `solution.length`) or the reference steps (the survey field's), so the dungeon's
types do not change. `Problem.seed_sets` is `{"dev": dev_seeds, "test": test_seeds}`.

`EpisodeLike` is the protocol the runner and meter use: `steps`, `log`, `end_reason`, `on_step`,
`stop()`, `outcome()`, `add_scout()`. The dungeon `Episode` already satisfies it.

## Kit

`Kit` gains one field, `problem: str`. Everything else is unchanged for the dungeon. For the
survey:

| Field | Value |
| --- | --- |
| `tools` | the survey `TOOL_SCHEMAS` ([survey-tools.md](survey-tools.md)) |
| `base_prompt` | the survey `BASE_PROMPT` |
| `start` | the start cell view as a result JSON |
| `tool_node`, `add_scout`, `recursion_limit` | same rules as the dungeon's |

## Support table

```python
# apl/runner/registry.py
SUPPORTS = {
    "react": {"dungeon", "survey"},
    "mapstate": {"dungeon", "survey"},
    "mapstate_routes": {"dungeon"},
    "hybrid": {"dungeon"},
    "fanout": {"dungeon", "survey"},
    "rounds": {"dungeon", "survey"},
    "blackboard": {"dungeon", "survey"},
}
```

Refusal message (run planning and viewer): `hybrid does not play the survey problem (it plays:
dungeon)`.

## Import rule

Architectures may import from `apl` only: `apl.kit`, `apl.arch`, `apl.dungeon.tools`,
`apl.dungeon.results`, `apl.survey.tools`, `apl.survey.results`. The boundary test's `ALLOWED`
set gains the two survey modules.
