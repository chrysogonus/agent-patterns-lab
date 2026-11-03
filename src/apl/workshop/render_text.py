"""A workshop as text, for `apl workshop show` (specs/011 contracts/cli.md). For the experimenter
only: it shows every recipe and the reference plan."""

from apl.workshop.model import Workshop
from apl.workshop.plans import reference_calls


def tree_order(workshop: Workshop) -> list[str]:
    """Every craftable, depth first from the goal through every recipe, each once."""
    order: list[str] = []

    def walk(item: str) -> None:
        if item in order:
            return
        order.append(item)
        for recipe in workshop.recipes[item]:
            for name in recipe:
                if workshop.craftable(name):
                    walk(name)

    walk(workshop.goal)
    return order


def render_text(workshop: Workshop, route: bool = False) -> str:
    """The header, the stock, one line per craftable and, with `route`, the reference plan."""
    name = workshop.level.name if workshop.level else "custom"
    stock = ", ".join(
        f"{raw} {n}" + (" (scarce)" if raw in workshop.scarce else "")
        for raw, n in workshop.stock.items()
    )
    lines = [
        f"Workshop {name}, seed {workshop.seed}: goal {workshop.goal}; "
        f"reference {workshop.reference_steps} steps (optimal); budget {workshop.budget}",
        f"stock: {stock}",
    ]
    for item in tree_order(workshop):
        recipes = workshop.recipes[item]
        if len(recipes) == 1:
            lines.append(f"  {item}: {', '.join(recipes[0])}")
            continue
        chosen = workshop.reference_choice.get(item, 1)
        parts = []
        for k, recipe in enumerate(recipes, 1):
            mark = "* " if k == chosen else "! " if k == 1 else ""
            parts.append(mark + ", ".join(recipe))
        lines.append(f"  {item}: {' | '.join(parts)}")
    if route:
        said = []
        for tool, args in reference_calls(workshop):
            extra = f" {args['recipe']}" if tool == "craft" else ""
            said.append(f"{tool} {args['item']}{extra}")
        lines.append("reference: " + ", ".join(said))
    return "\n".join(lines) + "\n"
