"""The problem mock-up's lantern as a hand-built workshop, and helpers to play calls on it."""

from collections.abc import Mapping, Sequence

from apl.workshop.env import Episode
from apl.workshop.model import Workshop
from apl.workshop.plans import reference_calls
from apl.workshop.results import ToolResult

Call = tuple[str, Mapping[str, object]]

RECIPES = {
    "lantern": (("frame", "lens", "oil"),),
    "frame": (("iron bar",), ("wood", "resin")),
    "iron bar": (("coal", "iron ore"),),
    "lens": (("glass",),),
    "glass": (("sand", "coal"),),
    "oil": (("seeds",),),
}
STOCK = {"coal": 1, "iron ore": 2, "resin": 1, "sand": 2, "seeds": 1, "wood": 1}

REFERENCE: list[Call] = [
    ("inspect", {"item": "lantern"}),
    ("inspect", {"item": "frame"}),
    ("gather", {"item": "wood"}),
    ("gather", {"item": "resin"}),
    ("craft", {"item": "frame", "recipe": 2}),
    ("inspect", {"item": "lens"}),
    ("inspect", {"item": "glass"}),
    ("gather", {"item": "sand"}),
    ("gather", {"item": "coal"}),
    ("craft", {"item": "glass", "recipe": 1}),
    ("craft", {"item": "lens", "recipe": 1}),
    ("inspect", {"item": "oil"}),
    ("gather", {"item": "seeds"}),
    ("craft", {"item": "oil", "recipe": 1}),
    ("craft", {"item": "lantern", "recipe": 1}),
]


def lantern() -> Workshop:
    shell = Workshop(None, None, "lantern", RECIPES, STOCK, frozenset({"coal"}), {"frame": 2}, 0)
    return Workshop(
        None, None, "lantern", RECIPES, STOCK, frozenset({"coal"}), {"frame": 2},
        len(reference_calls(shell)),
    )  # fmt: skip


def call(episode: Episode, name: str, args: Mapping[str, object]) -> ToolResult:
    if name == "look":
        return episode.look()
    if name == "inspect":
        return episode.inspect(args.get("item"))
    if name == "gather":
        return episode.gather(args.get("item"))
    if name == "craft":
        return episode.craft(args.get("item"), args.get("recipe"))
    return episode.unknown(name)


def play(episode: Episode, calls: Sequence[Call]) -> None:
    for name, args in calls:
        if episode.end_reason is not None:
            return
        call(episode, name, args)
