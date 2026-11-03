"""A workshop as SVG, for the viewer and `apl workshop show --html` (specs/011 research R14).

Drawn as in the problem mock-up: one box per item in layers under the goal, an edge from each item
to each input (second recipes dashed), raw materials as a bottom row with their stock. Boxes carry
`data-item`, edges `data-from`, `data-to` and `data-recipe`; the reference plan's edges have the
class `w-ref`. The page fills `#badges` (held counts) from the frames.
"""

from apl.workshop.model import Workshop

BOX_W, BOX_H = 96, 26
GAP_X, GAP_Y = 12, 46
MARGIN = 14


def layers(workshop: Workshop) -> list[list[str]]:
    """Craftables in layers by their shortest depth from the goal; raw materials last."""
    depth = {workshop.goal: 0}
    queue = [workshop.goal]
    while queue:
        item = queue.pop(0)
        for recipe in workshop.recipes[item]:
            for name in recipe:
                if workshop.craftable(name) and name not in depth:
                    depth[name] = depth[item] + 1
                    queue.append(name)
    rows: list[list[str]] = [[] for _ in range(max(depth.values()) + 1)]
    for item, d in depth.items():
        rows[d].append(item)
    return [*rows, list(workshop.stock)]


def places(workshop: Workshop) -> dict[str, tuple[int, int]]:
    """Each item's box (x, y): rows centred on the widest one."""
    rows = layers(workshop)
    widest = max(len(r) for r in rows)
    width = widest * (BOX_W + GAP_X) - GAP_X
    out = {}
    for y, row in enumerate(rows):
        span = len(row) * (BOX_W + GAP_X) - GAP_X
        left = MARGIN + (width - span) // 2
        for x, item in enumerate(row):
            out[item] = (left + x * (BOX_W + GAP_X), MARGIN + y * (BOX_H + GAP_Y))
    return out


def _reference_edges(workshop: Workshop) -> set[tuple[str, str, int]]:
    found: set[tuple[str, str, int]] = set()

    def walk(item: str) -> None:
        k = workshop.reference_choice.get(item, 1)
        for name in workshop.recipes[item][k - 1]:
            found.add((item, name, k))
            if workshop.craftable(name):
                walk(name)

    walk(workshop.goal)
    return found


def svg(workshop: Workshop, animated: bool = False) -> str:
    """The boxes, edges and stock labels. `animated` adds the group the page fills."""
    at = places(workshop)
    width = max(x for x, _ in at.values()) + BOX_W + MARGIN
    height = max(y for _, y in at.values()) + BOX_H + MARGIN
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Workshop recipe tree">'
    ]
    reference = _reference_edges(workshop)
    for item, recipes in workshop.recipes.items():
        px, py = at[item]
        for k, recipe in enumerate(recipes, 1):
            for name in recipe:
                cx, cy = at[name]
                cls = f"w-edge r{k}" + (" w-ref" if (item, name, k) in reference else "")
                out.append(
                    f'<line class="{cls}" data-from="{item}" data-to="{name}" data-recipe="{k}" '
                    f'x1="{px + BOX_W // 2}" y1="{py + BOX_H}" x2="{cx + BOX_W // 2}" y2="{cy}"/>'
                )
    for item, (x, y) in at.items():
        kind = "goal" if item == workshop.goal else "raw" if workshop.raw(item) else "craft"
        scarce = " scarce" if item in workshop.scarce else ""
        out.append(
            f'<rect class="w-item {kind}{scarce}" data-item="{item}" x="{x}" y="{y}" '
            f'width="{BOX_W}" height="{BOX_H}" rx="5"/>'
        )
        label = item if not workshop.raw(item) else f"{item} ×{workshop.stock[item]}"
        out.append(
            f'<text class="w-label" data-label="{item}" x="{x + BOX_W // 2}" y="{y + 17}" '
            f'text-anchor="middle">{label}</text>'
        )
    if animated:
        out.append('<g id="badges"></g>')
    out.append("</svg>")
    return "\n".join(out)


def html(workshop: Workshop) -> str:
    style = (
        ".w-item{fill:#fff;stroke:#9ca3af}.w-item.goal{stroke:#7c3aed;stroke-width:2}"
        ".w-item.raw{fill:#f3f4f6}.w-item.scarce{stroke:#dc2626}.w-label{font:11px monospace;"
        "fill:#1f2328}.w-edge{stroke:#9ca3af;stroke-width:1.5}.w-edge.r2{stroke-dasharray:5 4}"
        ".w-edge.w-ref{stroke:#0891b2;stroke-width:2.5}"
    )
    name = workshop.level.name if workshop.level else "custom"
    return (
        f"<!doctype html><meta charset='utf-8'><title>Workshop {name} {workshop.seed}</title>"
        f"<style>{style}</style>{svg(workshop)}\n"
    )
